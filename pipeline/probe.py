"""Feasibility probe: can we get one full season of shot-level data from nba_api?

Makes a single ShotChartDetail request for every field-goal attempt in the
2025-26 regular season (player_id=0, team_id=0 means "all players, all teams"),
caches the raw JSON in data/raw/, and prints a short summary.

Run from the project root:  .venv/bin/python pipeline/probe.py
"""

import json
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import shotchartdetail

SEASON = "2025-26"
RAW_DIR = Path("data/raw")
RAW_FILE = RAW_DIR / f"shotchart_{SEASON}_regular.json"
# Found by this probe: stats.nba.com returns at most this many rows per request
ROW_CAP = 102_400

# Columns PLAN.md says we need
NEEDED = [
    "GAME_ID", "GAME_EVENT_ID", "PLAYER_ID", "PLAYER_NAME", "TEAM_ID",
    "PERIOD", "MINUTES_REMAINING", "SECONDS_REMAINING", "SHOT_MADE_FLAG",
    "SHOT_DISTANCE", "SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "LOC_X", "LOC_Y",
    "ACTION_TYPE", "SHOT_TYPE",
]


def fetch_raw():
    """Return the raw JSON for the season, downloading only if not cached."""
    if RAW_FILE.exists():
        print(f"Using cached {RAW_FILE}")
        return json.loads(RAW_FILE.read_text())

    print(f"Requesting {SEASON} regular season from stats.nba.com ...")
    start = time.time()
    endpoint = shotchartdetail.ShotChartDetail(
        team_id=0,
        player_id=0,
        context_measure_simple="FGA",
        season_nullable=SEASON,
        season_type_all_star="Regular Season",
        timeout=180,  # one season is a large response
    )
    raw = endpoint.get_dict()
    print(f"Downloaded in {time.time() - start:.0f} s")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RAW_FILE.write_text(json.dumps(raw))
    return raw


def main():
    raw = fetch_raw()
    # The response holds several tables ("result sets"); shots are in Shot_Chart_Detail
    result = next(r for r in raw["resultSets"] if r["name"] == "Shot_Chart_Detail")
    shots = pd.DataFrame(result["rowSet"], columns=result["headers"])

    print(f"\nRows (field-goal attempts): {len(shots):,}")
    if len(shots) == ROW_CAP:
        print(f"WARNING: exactly {ROW_CAP:,} rows = server row cap; the response is truncated")
    print(f"Players: {shots['PLAYER_ID'].nunique()}   Games: {shots['GAME_ID'].nunique()}")
    print(f"Overall FG%: {shots['SHOT_MADE_FLAG'].mean():.3f}")
    print(f"Date range: {shots['GAME_DATE'].min()} to {shots['GAME_DATE'].max()}")

    missing = [c for c in NEEDED if c not in shots.columns]
    print(f"Missing needed columns: {missing or 'none'}")
    print(f"Null values in needed columns: {int(shots[NEEDED].isna().sum().sum())}")

    print("\nTop 5 players by attempts:")
    print(shots["PLAYER_NAME"].value_counts().head(5).to_string())

    print("\nFirst 3 rows (needed columns):")
    print(shots[NEEDED].head(3).to_string())


if __name__ == "__main__":
    main()
