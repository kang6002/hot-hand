"""Sensitivity check: how much do putbacks and tip-ins drive the result?

Putbacks and tip-ins mostly follow misses and go in often, which raises FG% after
misses and pushes the effect down. Here we drop them from every player's shot
sequence and rerun the whole analysis on the same tested players as the main run.

Run from the project root (after analyse.py):  .venv/bin/python pipeline/sensitivity_putbacks.py 2025-26
Output: data/processed/<season>/sensitivity_no_putbacks/{streaks,league,comparison}.csv
"""

import argparse

import numpy as np
import pandas as pd

from analyse import INTERIM_DIR, MIN_FGA, PROCESSED_DIR, analyse_season, print_league
from stats import KS

PUTBACK_TYPES = ("Tip Layup Shot", "Putback Layup Shot", "Tip Dunk Shot", "Putback Dunk Shot")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("season", nargs="?", default="2025-26")
    season = parser.parse_args().season
    folder = PROCESSED_DIR / season

    shots = pd.read_parquet(INTERIM_DIR / f"shots_{season}.parquet")
    main_players = pd.read_csv(folder / "players.csv")
    main_streaks = pd.read_csv(folder / "streaks.csv")
    main_league = pd.read_csv(folder / "league.csv")
    tested_ids = set(main_players.loc[main_players["tested"], "player_id"])

    is_putback = shots["ACTION_TYPE"].isin(PUTBACK_TYPES)
    kept = shots[~is_putback]  # keeps clean.py's shot order
    in_tested = shots["PLAYER_ID"].isin(tested_ids)
    print(f"{season}: removing {is_putback.sum():,} putbacks/tip-ins ({is_putback.mean():.1%} of shots; "
          f"{is_putback[in_tested].mean():.1%} of tested players' shots), FG% {shots.loc[is_putback, 'SHOT_MADE_FLAG'].mean():.1%}")
    below = (kept[kept["PLAYER_ID"].isin(tested_ids)].groupby("PLAYER_ID").size() < MIN_FGA).sum()
    print(f"Testing the same {len(tested_ids)} players as the main run ({below} now have < {MIN_FGA} FGA)")

    players, streaks, league, _ = analyse_season(kept, tested_ids)
    print_league(league)

    # Compare with the main run
    rows = []
    for k in KS:
        m = main_league[main_league["k"] == k].iloc[0]
        s = league[league["k"] == k].iloc[0]
        a = main_streaks[(main_streaks["k"] == k) & main_streaks["p_value"].notna()].set_index("player_id")
        b = streaks[(streaks["k"] == k) & streaks["p_value"].notna()].set_index("player_id")
        both = a.join(b, how="inner", suffixes=("_main", "_np"))
        rows.append({
            "k": k,
            "effect_main": m["effect"], "ci_low_main": m["ci_low"], "ci_high_main": m["ci_high"],
            "effect_no_putbacks": s["effect"], "ci_low_no_putbacks": s["ci_low"], "ci_high_no_putbacks": s["ci_high"],
            "p_value_no_putbacks": s["p_value"],
            "change": s["effect"] - m["effect"],
            "share_explained": 1 - s["effect"] / m["effect"],
            "discoveries_main": int(m["discoveries_hot"] + m["discoveries_cold"]),
            "discoveries_no_putbacks": int(s["discoveries_hot"] + s["discoveries_cold"]),
            "player_effect_correlation": both["effect_main"].corr(both["effect_np"]),
            "raw_after_misses_main": np.average(a["pct_after_misses"], weights=a["n_after_misses"]),
            "raw_after_misses_no_putbacks": np.average(b["pct_after_misses"], weights=b["n_after_misses"]),
        })
    comparison = pd.DataFrame(rows)

    out_dir = folder / "sensitivity_no_putbacks"
    out_dir.mkdir(parents=True, exist_ok=True)
    streaks.to_csv(out_dir / "streaks.csv", index=False)
    league.to_csv(out_dir / "league.csv", index=False)
    comparison.to_csv(out_dir / "comparison.csv", index=False)

    print("\nMain run vs without putbacks/tip-ins (league-wide effect, pp):")
    for r in comparison.itertuples():
        print(f"  k={r.k}: {100 * r.effect_main:+.2f} [{100 * r.ci_low_main:+.2f}, {100 * r.ci_high_main:+.2f}]"
              f"  ->  {100 * r.effect_no_putbacks:+.2f} [{100 * r.ci_low_no_putbacks:+.2f}, {100 * r.ci_high_no_putbacks:+.2f}]"
              f"  (change {100 * r.change:+.2f} pp, {r.share_explained:.0%} of the main effect)"
              f"  | raw FG% after misses {100 * r.raw_after_misses_main:.1f}% -> {100 * r.raw_after_misses_no_putbacks:.1f}%"
              f"  | player effects r = {r.player_effect_correlation:.2f}"
              f"  | discoveries {r.discoveries_main} -> {r.discoveries_no_putbacks}")
    print(f"\nSaved {out_dir}/")


if __name__ == "__main__":
    main()
