"""First and last NBA season of every player, to flag careers that began before
shot-level data starts (1996-97). One request to CommonAllPlayers, cached.

Run from the project root:  .venv/bin/python pipeline/player_info.py
Output: data/processed/player_info.csv (player_id, name, from_year, to_year, partial_career)
"""

import json
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import commonallplayers

from download import FIRST_SEASON

RAW = Path("data/raw/players/commonallplayers.json")
OUT = Path("data/processed/player_info.csv")


def main():
    if RAW.exists():
        raw = json.loads(RAW.read_text())
    else:
        raw = commonallplayers.CommonAllPlayers(is_only_current_season=0, timeout=60).get_dict()
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_text(json.dumps(raw))
    table = raw["resultSets"][0]
    df = pd.DataFrame(table["rowSet"], columns=table["headers"])
    info = pd.DataFrame({
        "player_id": df["PERSON_ID"].astype(int),
        "name": df["DISPLAY_FIRST_LAST"],
        # FROM_YEAR 1995 = the 1995-96 season
        "from_year": pd.to_numeric(df["FROM_YEAR"], errors="coerce").astype("Int64"),
        "to_year": pd.to_numeric(df["TO_YEAR"], errors="coerce").astype("Int64"),
    })
    info["partial_career"] = info["from_year"] < FIRST_SEASON
    OUT.parent.mkdir(parents=True, exist_ok=True)
    info.to_csv(OUT, index=False)
    print(f"{len(info):,} players; saved {OUT}")


if __name__ == "__main__":
    main()
