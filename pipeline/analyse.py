"""Run the hot-hand analysis for every player in one season.

- Every player: raw FG% overall and after k makes / k misses (Wilson CIs).
- Players with >= MIN_FGA attempts: bias-corrected permutation test for k = 1, 2, 3,
  with extra shuffles when the result is extreme, then BH-FDR across players per k.
- League-wide estimate per k: shot-weighted mean of the players' effects.

Run from the project root (after clean.py):  .venv/bin/python pipeline/analyse.py 2025-26
Outputs:
  data/processed/<season>/players.csv   one row per player
  data/processed/<season>/streaks.csv   one row per player and k (raw FG% + test)
  data/processed/<season>/league.csv    one row per k
  data/interim/draws_<season>.npz       null and bootstrap draws (for plots)
"""

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from stats import KS, N_PERM, analyse_player, benjamini_hochberg, descriptive

MIN_FGA = 300           # PLAN.md: minimum attempts to run the test
MAX_PERM = 1_000_000    # most shuffles for one player
MIN_EXTREME = 100       # add shuffles until this many are as extreme as the data
FDR_Q = 0.05
PROCESSED_DIR = Path("data/processed")
INTERIM_DIR = Path("data/interim")


def test_player(made, game, player_id):
    """analyse_player with extra shuffles for extreme results.

    With B shuffles the smallest p-value is 1/(B+1), too coarse for BH across
    hundreds of players. If fewer than MIN_EXTREME shuffles are as extreme as the
    data (for any k), rerun with 10x more shuffles, up to MAX_PERM.
    """
    n_perm = N_PERM
    while True:
        result = analyse_player(made, game, n_perm=n_perm, seed=[int(player_id), n_perm])
        # p = (b + 1) / (B + 1), so b = p (B + 1) - 1 shuffles were as extreme
        extreme = [r["p_value"] * (r["n_null_valid"] + 1) - 1 for r in result.values()]
        if np.nanmin(extreme) >= MIN_EXTREME or n_perm >= MAX_PERM:
            return result, n_perm
        n_perm *= 10


def league_estimate(rows, null_draws, null_means, boot_draws, weights):
    """Shot-weighted league effect, with a null and a CI built draw by draw across players."""
    w = np.asarray(weights, dtype=float)
    effect = np.sum(w * rows["effect"].to_numpy()) / w.sum()

    # Null: combine shuffle b of every player (independent players, so this is a
    # draw from the league-wide null). Centre each player at its own null mean.
    deviations = np.nan_to_num(null_draws - null_means[:, None])
    league_null = w @ deviations / w.sum()
    extreme = np.abs(league_null) >= abs(effect) - 1e-12
    p_value = (extreme.sum() + 1) / (len(league_null) + 1)

    # CI: combine bootstrap sample b of every player (skipping a player's rare NaN draws)
    valid = ~np.isnan(boot_draws)
    league_boot = (w @ np.where(valid, boot_draws, 0)) / (w @ valid)
    ci_low, ci_high = np.percentile(league_boot, [2.5, 97.5])
    return effect, ci_low, ci_high, p_value


def analyse_season(shots, tested_ids=None):
    """Raw stats for every player; test, BH-FDR and league estimate for tested players.

    shots must be in clean.py's order (player, game, game clock). tested_ids: which
    players to test; default every player with >= MIN_FGA attempts.
    Returns (players, streaks, league, draws).
    """
    players, streaks = [], []
    draws = {k: {"null": [], "boot": [], "null_mean": [], "fga": []} for k in KS}
    groups = list(shots.groupby("PLAYER_ID", sort=False))
    is_tested = (lambda pid, g: len(g) >= MIN_FGA) if tested_ids is None else (lambda pid, g: pid in tested_ids)
    n_tested = sum(is_tested(pid, g) for pid, g in groups)
    print(f"{len(groups)} players, {n_tested} tested")

    start = time.time()
    done = 0
    for player_id, g in groups:
        made, game = g["SHOT_MADE_FLAG"].to_numpy(), g["GAME_ID"].to_numpy()
        tested = is_tested(player_id, g)
        raw = descriptive(made, game)
        players.append({
            "player_id": player_id,
            "player_name": g["PLAYER_NAME"].iloc[-1],
            "fga": len(g),
            "games": g["GAME_ID"].nunique(),
            "fg_pct": raw["overall"]["pct"],
            "fg_ci_low": raw["overall"]["ci_low"],
            "fg_ci_high": raw["overall"]["ci_high"],
            "tested": tested,
        })

        result, n_perm = test_player(made, game, player_id) if tested else ({}, 0)
        for k in KS:
            row = {"player_id": player_id, "k": k}
            for cond in ("makes", "misses"):
                d = raw[f"after_{k}_{cond}"]
                row |= {f"n_after_{cond}": d["n"], f"pct_after_{cond}": d["pct"],
                        f"ci_low_after_{cond}": d["ci_low"], f"ci_high_after_{cond}": d["ci_high"]}
            if tested:
                r = result[k]
                row |= {"d_raw": r["d_obs"], "bias": r["null_mean"], "effect": r["effect"],
                        "ci_low": r["ci_low"], "ci_high": r["ci_high"],
                        "p_value": r["p_value"], "n_shuffles": n_perm}
                # keep the first N_PERM shuffles so every player contributes equally to the league null
                draws[k]["null"].append(r["null_draws"][:N_PERM].astype(np.float32))
                draws[k]["boot"].append(r["boot_draws"].astype(np.float32))
                draws[k]["null_mean"].append(r["null_mean"])
                draws[k]["fga"].append(len(g))
            streaks.append(row)

        if tested:
            done += 1
            if n_perm > N_PERM:
                print(f"  {g['PLAYER_NAME'].iloc[-1]}: extreme result, used {n_perm:,} shuffles")
            if done % 50 == 0:
                print(f"  {done}/{n_tested} tested ({time.time() - start:.0f} s)")
    print(f"Tests done in {time.time() - start:.0f} s")

    players = pd.DataFrame(players)
    streaks = pd.DataFrame(streaks)

    # BH-FDR across tested players, separately for each k
    streaks["q_value"] = np.nan
    streaks["discovery"] = pd.NA
    league = []
    for k in KS:
        rows = streaks[(streaks["k"] == k) & streaks["p_value"].notna()]
        reject, adjusted = benjamini_hochberg(rows["p_value"], q=FDR_Q)
        streaks.loc[rows.index, "q_value"] = adjusted
        streaks.loc[rows.index, "discovery"] = reject

        d = draws[k]
        null, boot = np.vstack(d["null"]), np.vstack(d["boot"])
        effect, ci_low, ci_high, p_value = league_estimate(
            rows, null, np.array(d["null_mean"]), boot, d["fga"]
        )
        league.append({
            "k": k, "n_players": len(rows), "effect": effect, "ci_low": ci_low,
            "ci_high": ci_high, "p_value": p_value,
            "discoveries_hot": int((reject & (rows["effect"] > 0)).sum()),
            "discoveries_cold": int((reject & (rows["effect"] < 0)).sum()),
        })
    return players, streaks, pd.DataFrame(league), draws


def print_league(league):
    print("\nLeague-wide (shot-weighted mean of player effects, percentage points):")
    for r in league.itertuples():
        print(f"  k={r.k}: {100 * r.effect:+.2f} pp  95% CI [{100 * r.ci_low:+.2f}, {100 * r.ci_high:+.2f}]"
              f"  p = {r.p_value:.4f}  BH discoveries: {r.discoveries_hot} hot, {r.discoveries_cold} cold"
              f"  (of {r.n_players})")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("season", nargs="?", default="2025-26")
    season = parser.parse_args().season

    print(f"Season {season}")
    shots = pd.read_parquet(INTERIM_DIR / f"shots_{season}.parquet")
    players, streaks, league, draws = analyse_season(shots)

    out_dir = PROCESSED_DIR / season
    out_dir.mkdir(parents=True, exist_ok=True)
    players.to_csv(out_dir / "players.csv", index=False)
    streaks.to_csv(out_dir / "streaks.csv", index=False)
    league.to_csv(out_dir / "league.csv", index=False)
    tested_ids = players.loc[players["tested"], "player_id"].to_numpy()
    np.savez_compressed(
        INTERIM_DIR / f"draws_{season}.npz", player_id=tested_ids,
        **{f"{kind}_k{k}": np.vstack(draws[k][kind]) for k in KS for kind in ("null", "boot")},
    )
    print_league(league)
    print(f"\nSaved {out_dir}/players.csv, streaks.csv, league.csv")


if __name__ == "__main__":
    main()
