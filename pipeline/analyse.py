"""Run the hot-hand analysis: one season (Milestone 1), careers, or per-season estimates.

- Every player: raw FG% overall and after k makes / k misses (Wilson CIs).
- Tested players: bias-corrected permutation test for k = 1, 2, 3 (stats.py).
- League-wide estimate per k: shot-weighted mean of the tested players' effects.

Run from the project root (after clean.py):
  .venv/bin/python pipeline/analyse.py 2025-26       one season, test + BH (Milestone 1)
  .venv/bin/python pipeline/analyse.py career        careers 1996-97..2025-26: test + BH (main result)
  .venv/bin/python pipeline/analyse.py seasons all   per-season estimates + CIs, no significance flags
Outputs:
  data/processed/<season>/{players,streaks,league}.csv     (one season)
  data/processed/career/{players,streaks,league}.csv       (careers)
  data/processed/seasons/{players,streaks,league}.csv      (every player-season, with a season column)
  data/interim/draws_<season|career>.npz                   null and bootstrap draws (for plots)
"""

import argparse
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# One maths thread per worker process: we already run one process per CPU core, and letting
# each also start ~13 threads (Apple Accelerate's default) oversubscribes the CPU.
# Must be set before numpy is imported.
for var in ("VECLIB_MAXIMUM_THREADS", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(var, "1")

import numpy as np  # noqa: E402
import pandas as pd

from download import all_seasons
from stats import KS, N_PERM, analyse_player, benjamini_hochberg, descriptive

MIN_FGA = 300           # PLAN.md: minimum attempts to run the test
MAX_PERM = 1_000_000    # most shuffles for one player
MIN_EXTREME = 100       # add shuffles until this many are as extreme as the data
FDR_Q = 0.05
SEASON_N_PERM = 2_000   # per-season runs only need the bias (null mean) and a CI, not a p-value
PROCESSED_DIR = Path("data/processed")
INTERIM_DIR = Path("data/interim")


def test_player(made, game, seed_key, n_perm=N_PERM, adaptive=True, certain_below=0.0):
    """analyse_player, with extra shuffles for extreme results if adaptive.

    With B shuffles the smallest p-value is 1/(B+1), too coarse for BH across
    hundreds of players. A k is settled when at least MIN_EXTREME shuffles are as
    extreme as the data (p precise to about 10%), or when p <= certain_below:
    BH always flags a p-value at or below q / (number of tests), so more
    shuffles couldn't change the result. Otherwise rerun with 10x more shuffles,
    up to MAX_PERM.
    seed_key (e.g. (player_id,) or (player_id, season year)) makes every run reproducible.
    """
    while True:
        result = analyse_player(made, game, n_perm=n_perm, seed=[*map(int, seed_key), n_perm])
        # p = (b + 1) / (B + 1), so b = p (B + 1) - 1 shuffles were as extreme
        settled = [np.isnan(r["p_value"]) or r["p_value"] <= certain_below
                   or r["p_value"] * (r["n_null_valid"] + 1) - 1 >= MIN_EXTREME
                   for r in result.values()]
        if not adaptive or all(settled) or n_perm >= MAX_PERM:
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


def player_task(task):
    """Everything for one player (runs in a worker process)."""
    player_id, name, made, game, tested, seed_key, n_perm, adaptive, certain_below = task
    raw = descriptive(made, game)
    player = {
        "player_id": player_id, "player_name": name, "fga": len(made),
        "games": len(np.unique(game)), "fg_pct": raw["overall"]["pct"],
        "fg_ci_low": raw["overall"]["ci_low"], "fg_ci_high": raw["overall"]["ci_high"],
        "tested": tested,
    }
    result, used = test_player(made, game, seed_key, n_perm, adaptive, certain_below) if tested else ({}, 0)
    rows, draws = [], {}
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
                    "p_value": r["p_value"], "n_shuffles": used}
            # keep the first n_perm shuffles so every player contributes equally to the league null
            draws[k] = (r["null_draws"][:n_perm].astype(np.float32), r["boot_draws"].astype(np.float32), r["null_mean"])
        rows.append(row)
    return player, rows, draws, used


def analyse_players(shots, tested_ids=None, n_perm=N_PERM, adaptive=True, fdr=True, seed_extra=(), workers=None, label=""):
    """Raw stats for every player; test, (optional) BH-FDR and league estimate for tested players.

    shots must be in clean.py's order (player, game, game clock); each game's shots contiguous.
    tested_ids: which players to test (default: every player with >= MIN_FGA attempts).
    Players run in parallel on all CPU cores. Returns (players, streaks, league, draws).
    """
    groups = list(shots.groupby("PLAYER_ID", sort=False))
    is_tested = [len(g) >= MIN_FGA if tested_ids is None else pid in tested_ids for pid, g in groups]
    n_tested = sum(is_tested)
    # A p-value at or below q / (number of tests) is always a BH discovery
    certain_below = FDR_Q / n_tested if fdr and n_tested else 0.0
    tasks = [(pid, g["PLAYER_NAME"].iloc[-1], g["SHOT_MADE_FLAG"].to_numpy(), g["GAME_ID"].to_numpy(),
              tested, (pid, *seed_extra), n_perm, adaptive, certain_below)
             for (pid, g), tested in zip(groups, is_tested)]
    print(f"{label}{len(tasks)} players, {n_tested} tested")

    # Biggest players first, one at a time per worker, so no core is left with huge careers at the end.
    # Results are collected as they finish (for progress) and put back in the original order.
    order = sorted(range(len(tasks)), key=lambda i: -len(tasks[i][2]) * tasks[i][4])
    results = [None] * len(tasks)
    start = time.time()
    with ProcessPoolExecutor(max_workers=workers or os.cpu_count()) as pool:
        futures = {pool.submit(player_task, tasks[i]): i for i in order}
        for done, future in enumerate(as_completed(futures), 1):
            out = future.result()
            results[futures[future]] = out
            if out[3] > n_perm:
                print(f"  {out[0]['player_name']}: extreme result, used {out[3]:,} shuffles ({time.time() - start:.0f} s)")
            if done % 250 == 0:
                print(f"  {done}/{len(tasks)} players ({time.time() - start:.0f} s)")
    print(f"{label}done in {time.time() - start:.0f} s")

    players = pd.DataFrame([r[0] for r in results])
    streaks = pd.DataFrame([row for r in results for row in r[1]])
    draws = {k: {"null": [], "boot": [], "null_mean": [], "fga": []} for k in KS}
    for player, _, d, _ in results:
        for k, (null, boot, null_mean) in d.items():
            draws[k]["null"].append(null)
            draws[k]["boot"].append(boot)
            draws[k]["null_mean"].append(null_mean)
            draws[k]["fga"].append(player["fga"])

    league = []
    if fdr:  # BH-FDR across tested players, separately for each k
        streaks["q_value"] = np.nan
        streaks["discovery"] = pd.NA
    for k in KS:
        rows = streaks[(streaks["k"] == k) & streaks["p_value"].notna()] if "p_value" in streaks else streaks.iloc[:0]
        if rows.empty:
            continue
        entry = {"k": k, "n_players": len(rows)}
        if fdr:
            reject, adjusted = benjamini_hochberg(rows["p_value"], q=FDR_Q)
            streaks.loc[rows.index, "q_value"] = adjusted
            streaks.loc[rows.index, "discovery"] = reject
        d = draws[k]
        effect, ci_low, ci_high, p_value = league_estimate(
            rows, np.vstack(d["null"]), np.array(d["null_mean"]), np.vstack(d["boot"]), d["fga"]
        )
        entry |= {"effect": effect, "ci_low": ci_low, "ci_high": ci_high, "p_value": p_value}
        if fdr:
            entry |= {"discoveries_hot": int((reject & (rows["effect"] > 0)).sum()),
                      "discoveries_cold": int((reject & (rows["effect"] < 0)).sum())}
        league.append(entry)
    return players, streaks, pd.DataFrame(league), draws


def analyse_season(shots, tested_ids=None):
    """Milestone 1 single-season analysis (test + extra shuffles + BH)."""
    return analyse_players(shots, tested_ids)


def print_league(league):
    print("\nLeague-wide (shot-weighted mean of player effects, percentage points):")
    for r in league.itertuples():
        disc = (f"  BH discoveries: {r.discoveries_hot} hot, {r.discoveries_cold} cold"
                if hasattr(r, "discoveries_hot") else "")
        print(f"  k={r.k}: {100 * r.effect:+.2f} pp  95% CI [{100 * r.ci_low:+.2f}, {100 * r.ci_high:+.2f}]"
              f"  p = {r.p_value:.4f}{disc}  (of {r.n_players})")


def save(folder, players, streaks, league, draws=None, draws_name=None):
    folder.mkdir(parents=True, exist_ok=True)
    players.to_csv(folder / "players.csv", index=False)
    streaks.to_csv(folder / "streaks.csv", index=False)
    league.to_csv(folder / "league.csv", index=False)
    if draws is not None:
        tested_ids = players.loc[players["tested"], "player_id"].to_numpy()
        np.savez_compressed(
            INTERIM_DIR / f"draws_{draws_name}.npz", player_id=tested_ids,
            **{f"{kind}_k{k}": np.vstack(draws[k][kind]) for k in KS for kind in ("null", "boot")},
        )
    print(f"Saved {folder}/players.csv, streaks.csv, league.csv")


def load_shots(seasons):
    """All shots of these seasons, in clean.py's order within each season."""
    return pd.concat([pd.read_parquet(INTERIM_DIR / f"shots_{s}.parquet") for s in seasons], ignore_index=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("what", nargs="?", default="2025-26", help='a season, "career" or "seasons"')
    parser.add_argument("seasons", nargs="*", help='with "seasons": which seasons, or "all"')
    args = parser.parse_args()

    if args.what == "career":
        shots = load_shots(all_seasons())
        # Group each player's shots together; games stay contiguous and in shot order
        shots = shots.sort_values(["PLAYER_ID", "GAME_ID", "ELAPSED_SECONDS", "GAME_EVENT_ID"], ignore_index=True)
        players, streaks, league, draws = analyse_players(shots, label="Careers: ")
        save(PROCESSED_DIR / "career", players, streaks, league, draws, "career")
        print_league(league)

    elif args.what == "seasons":
        seasons = all_seasons() if args.seasons in ([], ["all"]) else args.seasons
        out = {"players": [], "streaks": [], "league": []}
        for season in seasons:
            shots = load_shots([season])
            players, streaks, league, _ = analyse_players(
                shots, n_perm=SEASON_N_PERM, adaptive=False, fdr=False,
                seed_extra=(int(season[:4]),), label=f"{season}: ")
            for name, table in zip(out, (players, streaks, league)):
                out[name].append(table.assign(season=season))
        save(PROCESSED_DIR / "seasons", *(pd.concat(out[n], ignore_index=True) for n in out))

    else:  # one season, Milestone 1 style
        season = args.what
        print(f"Season {season}")
        players, streaks, league, draws = analyse_season(load_shots([season]))
        save(PROCESSED_DIR / season, players, streaks, league, draws, season)
        print_league(league)


if __name__ == "__main__":
    main()
