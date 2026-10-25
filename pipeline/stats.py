"""Hot-hand statistics for one player (PLAN.md § Statistics).

Input: a player's shot outcomes (1 = make, 0 = miss) in game order, plus the game
each shot belongs to; each game's shots must be contiguous. For k = 1, 2, 3:

  D_k     = P(make | previous k shots in the same game all makes)
          - P(make | previous k shots in the same game all misses), counts pooled over games
  null    = D_k after shuffling outcomes within each game (keeps each game's make count)
  effect  = D_k - mean(null)   (removes the Miller & Sanjurjo bias and the effect of
                                pooling good and bad nights)
  p-value = two-sided, distance from the null mean, (b + 1) / (B + 1)
  95% CI  = game-level bootstrap of the effect, re-estimating the bias in every bootstrap sample
"""

import warnings

import numpy as np
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint

KS = (1, 2, 3)
N_PERM = 10_000        # shuffles for the null distribution
N_BOOT = 2_000         # bootstrap samples for the CI
N_PERM_CI = 1_000      # shuffles reused to estimate the bias inside each bootstrap sample
CHUNK_CELLS = 5_000_000  # max (sequences x shots) held in memory at once


def game_starts(game):
    """Index of each game's first shot. Fails if a game's shots are not contiguous."""
    game = np.asarray(game)
    starts = np.concatenate([[0], np.flatnonzero(game[1:] != game[:-1]) + 1])
    if len(np.unique(game)) != len(starts):
        raise ValueError("each game's shots must be contiguous")
    return starts


def streak_counts(seqs, starts, k):
    """Per-game streak counts for a batch of shot sequences.

    seqs: (R, S) array of 0/1, R versions of the same S shots in game order.
    Returns an (R, G, 4) array with, per sequence and game: shots after k makes,
    makes among them, shots after k misses, makes among them. A shot only counts
    if its previous k shots are in the same game, so streaks never cross games.
    """
    R, S = seqs.shape
    lengths = np.diff(np.append(starts, S))
    position = np.arange(S) - np.repeat(starts, lengths)  # 0 = first shot of its game

    # Makes among the previous k shots, from a running total (cumsum[t] = makes before shot t)
    cumsum = np.zeros((R, S + 1), dtype=np.int32)
    np.cumsum(seqs, axis=1, out=cumsum[:, 1:])
    prev_makes = np.zeros((R, S), dtype=np.int32)
    if S > k:  # with S <= k no shot has k shots before it (and :S - k would wrap around)
        prev_makes[:, k:] = cumsum[:, k:S] - cumsum[:, :S - k]

    has_k_before = position >= k
    after_makes = (prev_makes == k) & has_k_before
    after_misses = (prev_makes == 0) & has_k_before
    made = seqs.astype(bool)
    cells = [after_makes, after_makes & made, after_misses, after_misses & made]
    return np.stack(
        [np.add.reduceat(c.astype(np.int32), starts, axis=1) for c in cells], axis=-1
    )


def streak_difference(counts):
    """D_k from summed counts (..., 4); NaN where either condition never happens."""
    n_after_makes, makes_after_makes, n_after_misses, makes_after_misses = (
        np.moveaxis(np.asarray(counts, dtype=float), -1, 0)
    )
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(
            (n_after_makes > 0) & (n_after_misses > 0),
            makes_after_makes / n_after_makes - makes_after_misses / n_after_misses,
            np.nan,
        )


def shuffled_within_games(made, starts, n, rng):
    """n copies of the shot sequence, each shuffled independently within every game."""
    bounds = zip(starts, np.append(starts[1:], len(made)))
    seqs = np.empty((n, len(made)), dtype=np.int8)
    for start, end in bounds:
        seqs[:, start:end] = rng.permuted(np.tile(made[start:end], (n, 1)), axis=1)
    return seqs


def two_sided_p(d_obs, null):
    """Share of null draws at least as far from the null mean as the observed value."""
    if np.isnan(d_obs) or len(null) == 0:
        return np.nan
    centre = null.mean()
    # small tolerance so exact ties (D takes few distinct values) count as extreme
    extreme = np.abs(null - centre) >= np.abs(d_obs - centre) - 1e-12
    return (extreme.sum() + 1) / (len(null) + 1)


def bootstrap_ci(obs_counts, perm_counts, n_boot, rng, level=0.95):
    """Game-level bootstrap CI of the bias-corrected effect: (low, high, bootstrap effects).

    obs_counts: (G, 4) observed per-game counts; perm_counts: (P, G, 4) per-game
    counts of P shuffles. A bootstrap sample is a vector of how often each game
    was drawn, so its counts (observed and shuffled) are weighted sums over games.
    """
    G = obs_counts.shape[0]
    weights = rng.multinomial(G, np.full(G, 1 / G), size=n_boot).astype(float)  # (n_boot, G)
    d_star = streak_difference(weights @ obs_counts)

    P = perm_counts.shape[0]
    by_game = perm_counts.transpose(1, 0, 2).reshape(G, P * 4).astype(float)
    null_star = streak_difference((weights @ by_game).reshape(n_boot, P, 4))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN rows (no streaks in a sample) give NaN
        effect_star = d_star - np.nanmean(null_star, axis=1)
    tail = (1 - level) / 2 * 100
    low, high = np.nanpercentile(effect_star, [tail, 100 - tail])
    return float(low), float(high), effect_star


def analyse_player(made, game, ks=KS, n_perm=N_PERM, n_boot=N_BOOT, n_perm_ci=N_PERM_CI, seed=0):
    """Bias-corrected hot-hand test for one player, for each k.

    Returns {k: dict} with the raw difference (d_obs), the null mean (the bias),
    the effect, p-value, CI, condition sizes, and the null and bootstrap draws
    (for plots and the league-wide estimate). Set n_boot=0 to skip the CI.
    """
    made = np.asarray(made, dtype=np.int8)
    starts = game_starts(game)
    rng = np.random.default_rng(seed)
    n_perm_ci = min(n_perm_ci, n_perm) if n_boot else 0

    null_draws = {k: np.empty(n_perm) for k in ks}
    ci_counts = {k: [] for k in ks}  # per-game counts of the first n_perm_ci shuffles
    chunk = max(1, CHUNK_CELLS // len(made))
    for lo in range(0, n_perm, chunk):
        n = min(chunk, n_perm - lo)
        seqs = shuffled_within_games(made, starts, n, rng)
        for k in ks:
            counts = streak_counts(seqs, starts, k)
            null_draws[k][lo:lo + n] = streak_difference(counts.sum(axis=1))
            if lo < n_perm_ci:
                ci_counts[k].append(counts[: n_perm_ci - lo])

    results = {}
    for k in ks:
        obs = streak_counts(made[None, :], starts, k)[0]  # (G, 4)
        totals = obs.sum(axis=0)
        d_obs = float(streak_difference(totals))
        null = null_draws[k][~np.isnan(null_draws[k])]
        null_mean = float(null.mean()) if len(null) else np.nan
        ci = (np.nan, np.nan, np.full(n_boot, np.nan))
        if n_boot and not np.isnan(d_obs):
            ci = bootstrap_ci(obs, np.concatenate(ci_counts[k]), n_boot, rng)
        results[k] = {
            "d_obs": d_obs,
            "null_mean": null_mean,
            "effect": d_obs - null_mean,
            "p_value": float(two_sided_p(d_obs, null)),
            "ci_low": ci[0],
            "ci_high": ci[1],
            "n_after_makes": int(totals[0]),
            "n_after_misses": int(totals[2]),
            "n_null_valid": int(len(null)),
            "null_draws": null_draws[k],
            "boot_draws": ci[2],
        }
    return results


def wilson(makes, n):
    """FG% with a 95% Wilson interval (NaN when n = 0)."""
    if n == 0:
        return {"makes": 0, "n": 0, "pct": np.nan, "ci_low": np.nan, "ci_high": np.nan}
    low, high = proportion_confint(makes, n, alpha=0.05, method="wilson")
    return {"makes": int(makes), "n": int(n), "pct": makes / n, "ci_low": low, "ci_high": high}


def descriptive(made, game, ks=KS):
    """Raw (uncorrected) FG% overall and after k makes / k misses in the same game."""
    made = np.asarray(made, dtype=np.int8)
    starts = game_starts(game)
    out = {"overall": wilson(made.sum(), len(made))}
    for k in ks:
        n1, a1, n0, a0 = streak_counts(made[None, :], starts, k)[0].sum(axis=0)
        out[f"after_{k}_makes"] = wilson(a1, n1)
        out[f"after_{k}_misses"] = wilson(a0, n0)
    return out


def benjamini_hochberg(p_values, q=0.05):
    """BH-FDR: (reject, adjusted p) arrays; NaN p-values are left out and stay NaN/False."""
    p = np.asarray(p_values, dtype=float)
    ok = ~np.isnan(p)
    reject = np.zeros(len(p), dtype=bool)
    adjusted = np.full(len(p), np.nan)
    if ok.any():
        reject[ok], adjusted[ok], _, _ = multipletests(p[ok], alpha=q, method="fdr_bh")
    return reject, adjusted
