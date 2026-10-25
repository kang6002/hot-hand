"""Write the static JSON files the website reads.

Run from the project root (after analyse.py):  .venv/bin/python pipeline/build_json.py 2025-26
Outputs in site/public/data/:
  index.json            every player (for search)
  league.json           league-wide result per k, every tested player's effect, power curve
  players/<id>.json     one file per player: raw FG%, test results, shuffle histogram, shot sequences
"""

import argparse
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from analyse import INTERIM_DIR, MIN_FGA, PROCESSED_DIR, FDR_Q
from stats import KS

SITE_DATA = Path("site/public/data")
HIST_BINS = 40
ATTRIBUTION = "Data: NBA.com Stats via nba_api. Not affiliated with or endorsed by the NBA."


def num(x, digits=4):
    """JSON-safe rounded number (NaN -> null)."""
    if x is None or (isinstance(x, float) and math.isnan(x)) or pd.isna(x):
        return None
    return round(float(x), digits)


def proportion(row, cond):
    return {
        "n": int(row[f"n_after_{cond}"]),
        "pct": num(row[f"pct_after_{cond}"]),
        "ci_low": num(row[f"ci_low_after_{cond}"]),
        "ci_high": num(row[f"ci_high_after_{cond}"]),
    }


def histogram(draws):
    """Shuffle distribution as a compact histogram (in proportions, like the effects)."""
    draws = draws[~np.isnan(draws)]
    counts, edges = np.histogram(draws, bins=HIST_BINS)
    return {"start": num(edges[0], 5), "width": num(edges[1] - edges[0], 5),
            "counts": counts.tolist(), "n": int(len(draws))}


def power_rows(path=PROCESSED_DIR / "power_curve.csv"):
    """Power curve from pipeline/power.py (empty if it hasn't been run)."""
    if not path.exists():
        return []
    power = pd.read_csv(path)
    return [{"k": int(r["k"]), "fga": int(r["fga"]), "boost": num(r["boost"]),
             "power_05": num(r["power_0.05"]), "power_001": num(r["power_0.001"])}
            for _, r in power.iterrows()]


def sensitivity_rows(path):
    """League result without putbacks/tip-ins (pipeline/sensitivity_putbacks.py), if it has been run."""
    if not path.exists():
        return []
    return [{"k": int(r.k), "effect": num(r.effect), "ci_low": num(r.ci_low), "ci_high": num(r.ci_high),
             "p_value": num(r.p_value, 6)} for r in pd.read_csv(path).itertuples()]


def player_json(season, p, rows, games, null_draws):
    """One player's file."""
    ks = []
    for k in KS:
        r = rows.loc[k]
        entry = {"k": k, "after_makes": proportion(r, "makes"), "after_misses": proportion(r, "misses")}
        if p["tested"]:
            entry["test"] = {
                "d_raw": num(r["d_raw"]), "bias": num(r["bias"]), "effect": num(r["effect"]),
                "ci_low": num(r["ci_low"]), "ci_high": num(r["ci_high"]),
                "p_value": num(r["p_value"], 6), "q_value": num(r["q_value"], 4),
                "discovery": str(r["discovery"]) == "True",
                "n_shuffles": int(r["n_shuffles"]),
                "null_hist": histogram(null_draws[k]) if null_draws else None,
            }
        ks.append(entry)
    return {
        "id": int(p["player_id"]), "name": p["player_name"], "season": season,
        "fga": int(p["fga"]), "games": int(p["games"]),
        "fg": {"pct": num(p["fg_pct"]), "ci_low": num(p["fg_ci_low"]), "ci_high": num(p["fg_ci_high"])},
        "tested": bool(p["tested"]), "min_fga": MIN_FGA, "fdr_q": FDR_Q,
        "ks": ks,
        "game_log": games,
        "attribution": ATTRIBUTION,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("season", nargs="?", default="2025-26")
    season = parser.parse_args().season

    folder = PROCESSED_DIR / season
    players = pd.read_csv(folder / "players.csv")
    streaks = pd.read_csv(folder / "streaks.csv")
    league = pd.read_csv(folder / "league.csv")
    draws = np.load(INTERIM_DIR / f"draws_{season}.npz")
    draw_row = {int(pid): i for i, pid in enumerate(draws["player_id"])}
    shots = pd.read_parquet(INTERIM_DIR / f"shots_{season}.parquet")  # already in shot order

    # Start from an empty players/ folder so removed players don't linger
    if (SITE_DATA / "players").exists():
        shutil.rmtree(SITE_DATA / "players")
    (SITE_DATA / "players").mkdir(parents=True)

    for player_id, g in shots.groupby("PLAYER_ID", sort=False):
        p = players[players["player_id"] == player_id].iloc[0]
        rows = streaks[streaks["player_id"] == player_id].set_index("k")
        games = [
            {"game_id": game_id, "date": gg["GAME_DATE"].iloc[0].strftime("%Y-%m-%d"),
             "shots": "".join(map(str, gg["SHOT_MADE_FLAG"]))}
            for game_id, gg in g.groupby("GAME_ID", sort=False)
        ]
        games.sort(key=lambda x: x["date"])
        null_draws = ({k: draws[f"null_k{k}"][draw_row[int(player_id)]] for k in KS}
                      if p["tested"] else None)
        data = player_json(season, p, rows, games, null_draws)
        (SITE_DATA / "players" / f"{int(player_id)}.json").write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False))

    index = [{"id": int(p.player_id), "name": p.player_name, "fga": int(p.fga), "tested": bool(p.tested)}
             for p in players.sort_values("player_name").itertuples()]
    (SITE_DATA / "index.json").write_text(json.dumps({"season": season, "players": index}, ensure_ascii=False))

    tested = streaks[streaks["p_value"].notna()].merge(players[["player_id", "player_name", "fga"]], on="player_id")
    league_json = {
        "season": season, "min_fga": MIN_FGA, "fdr_q": FDR_Q,
        "n_players": int(len(players)), "n_tested": int(players["tested"].sum()),
        "ks": [{"k": int(r.k), "n_players": int(r.n_players), "effect": num(r.effect), "ci_low": num(r.ci_low),
                "ci_high": num(r.ci_high), "p_value": num(r.p_value, 6),
                "discoveries_hot": int(r.discoveries_hot), "discoveries_cold": int(r.discoveries_cold)}
               for r in league.itertuples()],
        "players": [{"id": int(r.player_id), "name": r.player_name, "fga": int(r.fga), "k": int(r.k),
                     "effect": num(r.effect), "ci_low": num(r.ci_low), "ci_high": num(r.ci_high),
                     "q_value": num(r.q_value), "discovery": str(r.discovery) == "True"}
                    for r in tested.itertuples()],
        "power": power_rows(),
        "no_putbacks": sensitivity_rows(folder / "sensitivity_no_putbacks" / "league.csv"),
        "attribution": ATTRIBUTION,
    }
    (SITE_DATA / "league.json").write_text(json.dumps(league_json, separators=(",", ":"), ensure_ascii=False))

    size = sum(f.stat().st_size for f in SITE_DATA.rglob("*.json"))
    print(f"Wrote {len(index)} player files, index.json and league.json to {SITE_DATA} ({size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
