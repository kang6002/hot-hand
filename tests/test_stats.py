from itertools import permutations

import numpy as np
import pytest

from simulate import simulate_shooter
from stats import (analyse_player, benjamini_hochberg, descriptive, game_starts,
                   streak_counts, streak_difference)


def counts_for(made, game, k):
    """Totals (shots after k makes, makes among them, after k misses, makes) for one sequence."""
    made = np.array(made, dtype=np.int8)
    return tuple(int(c) for c in streak_counts(made[None, :], game_starts(game), k)[0].sum(axis=0))


# --- Hand-built sequences ----------------------------------------------------

def test_counts_k1_by_hand():
    # game A: 1 1 0 1   game B: 1 0
    # after a make: A2 (1), A3 (0), B2 (0) -> 3 shots, 1 make
    # after a miss: A4 (1)                 -> 1 shot, 1 make
    assert counts_for([1, 1, 0, 1, 1, 0], ["A"] * 4 + ["B"] * 2, k=1) == (3, 1, 1, 1)


def test_streaks_never_cross_games():
    # game A: 0 1 1   game B: 1 1 1
    # Within games, only B3 follows two makes. If streaks crossed games, B1 and B2
    # would also count (they follow A2-A3 and A3-B1), giving (3, 3, 0, 0).
    made = [0, 1, 1, 1, 1, 1]
    game = ["A"] * 3 + ["B"] * 3
    assert counts_for(made, game, k=2) == (1, 1, 0, 0)


def test_counts_k3_by_hand():
    # one game: 1 1 1 1 0 0 0 1
    # after 3 makes: shot 4 (1), shot 5 (0)  -> 2 shots, 1 make
    # after 3 misses: shot 8 (1)             -> 1 shot, 1 make
    assert counts_for([1, 1, 1, 1, 0, 0, 0, 1], ["A"] * 8, k=3) == (2, 1, 1, 1)


def test_fewer_shots_than_k():
    # A player with 2 career shots: nothing follows 3 makes or 3 misses
    assert counts_for([1, 1], ["A", "A"], k=3) == (0, 0, 0, 0)
    d = descriptive([1, 1], ["A", "A"])
    assert d["after_3_makes"]["n"] == 0 and np.isnan(d["after_3_makes"]["pct"])


def test_games_must_be_contiguous():
    with pytest.raises(ValueError):
        game_starts(["A", "B", "A"])


def test_difference_is_nan_when_a_condition_never_happens():
    assert np.isnan(streak_difference([0, 0, 5, 2]))
    assert streak_difference([4, 3, 2, 1]) == pytest.approx(0.75 - 0.5)


def test_null_mean_matches_exact_enumeration():
    # One game, 2 makes in 5 shots: average D_1 over all distinct orderings, by brute force
    made = [1, 1, 0, 0, 0]
    game = ["A"] * 5
    orders = set(permutations(made))
    exact = np.nanmean([streak_difference(counts_for(o, game, 1)) for o in orders])
    result = analyse_player(made, game, ks=(1,), n_perm=20_000, n_boot=0, seed=1)[1]
    assert result["null_mean"] == pytest.approx(exact, abs=0.01)
    assert exact < 0  # the Miller & Sanjurjo bias


def test_descriptive_matches_counts():
    d = descriptive([1, 1, 0, 1, 1, 0], ["A"] * 4 + ["B"] * 2)
    assert d["overall"]["pct"] == pytest.approx(4 / 6)
    assert d["after_1_makes"]["n"] == 3 and d["after_1_makes"]["makes"] == 1
    assert d["after_1_misses"]["n"] == 1 and d["after_1_misses"]["makes"] == 1
    assert d["overall"]["ci_low"] < 4 / 6 < d["overall"]["ci_high"]


def test_benjamini_hochberg_ignores_nan():
    reject, adjusted = benjamini_hochberg([0.001, np.nan, 0.5, 0.01], q=0.05)
    assert list(reject) == [True, False, False, True]
    assert np.isnan(adjusted[1])


# --- Simulated shooters ------------------------------------------------------

def naive_and_corrected(n_players, k, seed, **shooter):
    """Mean raw difference and mean corrected effect over simulated players."""
    rng = np.random.default_rng(seed)
    naive, corrected = [], []
    for i in range(n_players):
        made, game = simulate_shooter(rng, **shooter)
        r = analyse_player(made, game, ks=(k,), n_perm=300, n_boot=0, seed=i)[k]
        naive.append(r["d_obs"]); corrected.append(r["effect"])
    return np.nanmean(naive), np.nanmean(corrected)


def test_one_long_sequence_naive_is_biased_down_corrected_is_not():
    # Miller & Sanjurjo: one 100-shot sequence (like Gilovich et al.'s shooting
    # experiment), no hot hand. The raw difference is about -8 points for k = 3.
    naive, corrected = naive_and_corrected(300, 3, seed=0, n_games=1, shots_per_game=100, p=0.5)
    assert naive < -0.06
    assert corrected == pytest.approx(0, abs=0.02)


def test_good_and_bad_nights_naive_is_biased_up_corrected_is_not():
    # No hot hand, but make probability varies between games. Pooling games makes the
    # raw difference look like a hot hand; shuffling within games removes it.
    naive, corrected = naive_and_corrected(300, 3, seed=1, n_games=70, shots_per_game=15, game_sd=0.08)
    assert naive > 0.03
    assert corrected == pytest.approx(0, abs=0.02)


def test_strong_hot_hand_is_detected():
    rng = np.random.default_rng(2)
    made, game = simulate_shooter(rng, n_games=80, shots_per_game=18, boost=0.15, k=1)
    result = analyse_player(made, game, n_perm=2_000, n_boot=500, seed=0)
    for k in (1, 2, 3):
        assert result[k]["effect"] > 0
        assert result[k]["ci_low"] < result[k]["effect"] < result[k]["ci_high"]
    assert result[1]["p_value"] < 0.01
    assert result[1]["ci_low"] > 0


# --- Slow calibration checks (run with: pytest -m slow) ----------------------

def null_players(n_players, n_perm, seed):
    """p-values (per k) for simulated players with no hot hand, but good and bad nights."""
    rng = np.random.default_rng(seed)
    p = {k: [] for k in (1, 2, 3)}
    for i in range(n_players):
        made, game = simulate_shooter(rng, n_games=40, shots_per_game=12, game_sd=0.08)
        r = analyse_player(made, game, n_perm=n_perm, n_boot=0, seed=seed * 100_000 + i)
        for k in (1, 2, 3):
            p[k].append(r[k]["p_value"])
    return {k: np.array(v) for k, v in p.items()}


@pytest.mark.slow
def test_false_positive_rate_is_five_percent():
    # 2,000 players: a correct test lands in [3.8%, 6.2%] (about +-2.4 standard errors)
    # for all three k together 95% of the time.
    p = null_players(2_000, n_perm=1_000, seed=3)
    for k in (1, 2, 3):
        rate = np.mean(p[k][~np.isnan(p[k])] < 0.05)
        assert 0.038 <= rate <= 0.062, f"k={k}: false-positive rate {rate:.3f}"


@pytest.mark.slow
def test_null_league_has_no_bh_discoveries():
    # A league of 300 players without a hot hand, with the real number of shuffles.
    # BH keeps the chance of any false discovery at or below 5%.
    p = null_players(300, n_perm=10_000, seed=4)
    for k in (1, 2, 3):
        reject, _ = benjamini_hochberg(p[k], q=0.05)
        assert reject.sum() == 0, f"k={k}: {reject.sum()} discoveries"


@pytest.mark.slow
@pytest.mark.parametrize("boost", [0.0, 0.10])
def test_confidence_interval_coverage(boost):
    # The 95% CI should contain the estimator's true mean about 95% of the time. With no
    # hot hand that mean is 0; with a hot hand it is estimated from the simulations.
    # Measured: about 94% with 40 games (percentile bootstrap, few games); see DECISIONS.md.
    rng = np.random.default_rng(5)
    effects, lows, highs = [], [], []
    for i in range(2_000):
        made, game = simulate_shooter(rng, n_games=40, shots_per_game=12, game_sd=0.08, boost=boost)
        r = analyse_player(made, game, ks=(1,), n_perm=300, n_boot=1_000, n_perm_ci=300, seed=i)[1]
        effects.append(r["effect"]); lows.append(r["ci_low"]); highs.append(r["ci_high"])
    truth = 0.0 if boost == 0 else np.mean(effects)
    coverage = np.mean((np.array(lows) <= truth) & (truth <= np.array(highs)))
    print(f"boost={boost}: coverage {coverage:.3f}")
    assert 0.925 <= coverage <= 0.97, f"coverage {coverage:.3f}"
