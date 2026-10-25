"""Turn one season's cached monthly responses into a tidy, ordered table of shots.

Each row is one field-goal attempt. Shots are ordered within each player-game
by game clock, ties broken by GAME_EVENT_ID. GAME_EVENT_ID alone is the order
events were typed in, which is wrong for shots logged late (DECISIONS.md;
pipeline/check_order.py). EVENT_ID_OUT_OF_ORDER marks those shots: the ones
GAME_EVENT_ID order would have put too late.

Run from the project root (after download.py):  .venv/bin/python pipeline/clean.py 2025-26
Output: data/interim/shots_<season>.parquet
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from download import RAW_DIR, shot_rows

INTERIM_DIR = Path("data/interim")

KEEP = [
    "GAME_ID", "GAME_DATE", "GAME_EVENT_ID", "PLAYER_ID", "PLAYER_NAME", "TEAM_ID",
    "PERIOD", "MINUTES_REMAINING", "SECONDS_REMAINING", "SHOT_MADE_FLAG",
    "SHOT_DISTANCE", "SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "LOC_X", "LOC_Y",
    "ACTION_TYPE", "SHOT_TYPE",
]


def load_raw(season):
    """All cached monthly responses for a season as one DataFrame."""
    files = sorted((RAW_DIR / season).glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No cached data for {season}; run download.py first")
    frames = []
    for path in files:
        headers, rows = shot_rows(json.loads(path.read_text()))
        frames.append(pd.DataFrame(rows, columns=headers))
    return pd.concat(frames, ignore_index=True)


def elapsed_seconds(period, minutes_remaining, seconds_remaining):
    """Seconds since tip-off. Quarters last 12 minutes, overtimes 5."""
    remaining = minutes_remaining * 60 + seconds_remaining
    regulation = (period.clip(upper=4) - 1) * 720 + 720 - remaining
    overtime = 4 * 720 + (period - 5) * 300 + 300 - remaining
    return regulation.where(period <= 4, overtime)


def clean(raw, season):
    """Check, order and annotate the raw shots of one season."""
    # Sanity checks on the raw data; stop rather than analyse something odd
    assert (raw["SHOT_ATTEMPTED_FLAG"] == 1).all(), "non-attempt rows present"
    made_by_event = raw["EVENT_TYPE"].map({"Made Shot": 1, "Missed Shot": 0})
    assert (made_by_event == raw["SHOT_MADE_FLAG"]).all(), "EVENT_TYPE disagrees with SHOT_MADE_FLAG"
    assert not raw.duplicated(["GAME_ID", "GAME_EVENT_ID"]).any(), "duplicate shots"

    shots = raw[KEEP].copy()
    shots.insert(0, "SEASON", season)
    shots["GAME_DATE"] = pd.to_datetime(shots["GAME_DATE"], format="%Y%m%d")
    shots["ELAPSED_SECONDS"] = elapsed_seconds(
        shots["PERIOD"], shots["MINUTES_REMAINING"], shots["SECONDS_REMAINING"]
    )

    # Flag shots whose clock is earlier than the player's previous shot in GAME_EVENT_ID order
    shots = shots.sort_values(["PLAYER_ID", "GAME_ID", "GAME_EVENT_ID"], ignore_index=True)
    shots["EVENT_ID_OUT_OF_ORDER"] = (
        shots.groupby(["PLAYER_ID", "GAME_ID"])["ELAPSED_SECONDS"].diff() < 0
    )

    # The order used from here on: game clock, then GAME_EVENT_ID for shots in the same second
    shots = shots.sort_values(
        ["PLAYER_ID", "GAME_ID", "ELAPSED_SECONDS", "GAME_EVENT_ID"], ignore_index=True
    )
    # 1 = the player's first shot of the game, 2 = second, ...
    shots["SHOT_NUMBER"] = shots.groupby(["PLAYER_ID", "GAME_ID"]).cumcount() + 1
    return shots


def summarise(shots):
    """Print what a reader should check about the cleaned season."""
    n_flag = int(shots["EVENT_ID_OUT_OF_ORDER"].sum())
    player_games = shots.groupby(["PLAYER_ID", "GAME_ID"])
    flagged_games = int(player_games["EVENT_ID_OUT_OF_ORDER"].any().sum())
    teams_per_player_game = player_games["TEAM_ID"].nunique()
    # Shots by one player in the same second: only these rely on the GAME_EVENT_ID tie-break
    same_second = shots.duplicated(["PLAYER_ID", "GAME_ID", "ELAPSED_SECONDS"], keep=False)

    print(f"{len(shots):,} shots, {shots['PLAYER_ID'].nunique()} players, "
          f"{len(player_games):,} player-games")
    print(f"Players with >1 team in the same game: {int((teams_per_player_game > 1).sum())}")
    print(f"Shots GAME_EVENT_ID would misplace (fixed by clock order): {n_flag} "
          f"in {flagged_games} player-games ({n_flag / len(shots):.3%} of shots)")
    print(f"Shots sharing a second with another shot by the same player: {int(same_second.sum())}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("season", nargs="?", default="2025-26", help='e.g. "2025-26"')
    season = parser.parse_args().season

    shots = clean(load_raw(season), season)
    summarise(shots)

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    out = INTERIM_DIR / f"shots_{season}.parquet"
    shots.to_parquet(out, index=False)
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
