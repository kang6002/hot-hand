"""Power curve: how often does the test detect a hot hand of a given size?

Simulated shooters (pipeline/simulate.py) with a known hot hand: after k makes in a
row (same game), the make probability rises by BOOST. For each k, number of shots
and boost we simulate N_SIMS players and record how often p < alpha.

Run from the project root:  .venv/bin/python pipeline/power.py
Output: data/processed/power_curve.csv (plot it with pipeline/plots.py)
"""

import time
from concurrent.futures import ProcessPoolExecutor
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from simulate import simulate_shooter
from stats import analyse_player

KS = (1, 2, 3)
FGA = (300, 600, 1000, 1500, 3000, 6000, 12000, 24000)  # one season ... a long career
BOOSTS = (0.0, 0.02, 0.05, 0.10)          # rise in make probability after k makes
ALPHAS = (0.05, 0.001)                    # per-player level; 0.001 is roughly what BH needs
SHOTS_PER_GAME = 15
BASE_P = 0.46                             # league FG% 2025-26 is about 0.47
GAME_SD = 0.04                            # mild good and bad nights
N_SIMS = 200
N_PERM = 2_000                            # enough to resolve p <= 0.001
OUT = Path("data/processed/power_curve.csv")


def run_cell(args):
    """Simulate N_SIMS players for one (k, fga, boost) and summarise."""
    k, fga, boost_index = args
    boost = BOOSTS[boost_index]
    rng = np.random.default_rng([k, fga, boost_index])
    p_values, effects = [], []
    for i in range(N_SIMS):
        made, game = simulate_shooter(rng, n_games=fga // SHOTS_PER_GAME, shots_per_game=SHOTS_PER_GAME,
                                      p=BASE_P, game_sd=GAME_SD, boost=boost, k=k)
        r = analyse_player(made, game, ks=(k,), n_perm=N_PERM, n_boot=0, seed=[k, fga, boost_index, i])[k]
        p_values.append(r["p_value"]); effects.append(r["effect"])
    p = np.array(p_values)
    row = {"k": k, "fga": fga, "boost": boost, "n_sims": N_SIMS, "mean_effect": np.nanmean(effects)}
    for alpha in ALPHAS:
        row[f"power_{alpha}"] = np.mean(p[~np.isnan(p)] <= alpha)
    return row


def main():
    cells = list(product(KS, FGA, range(len(BOOSTS))))
    # Results are seeded per scenario, so scenarios already in the CSV don't need rerunning
    old = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=["k", "fga", "boost"])
    done = {(int(r.k), int(r.fga), float(r.boost)) for r in old.itertuples()}
    cells = [c for c in cells if (c[0], c[1], BOOSTS[c[2]]) not in done]
    print(f"{len(cells)} new scenarios x {N_SIMS} simulated players ({len(done)} already done) ...")
    start = time.time()
    with ProcessPoolExecutor() as pool:  # one scenario per CPU core at a time
        rows = list(pool.map(run_cell, cells))
    print(f"done in {time.time() - start:.0f} s")
    table = pd.concat([old, pd.DataFrame(rows)], ignore_index=True).sort_values(["k", "fga", "boost"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False)
    print(table.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
