"""Which shot order is right: GAME_EVENT_ID or the game clock?

GAME_EVENT_ID turned out to be the order events were typed in, so shots logged
late get a too-high id (DECISIONS.md). This script checks both orderings against
the NBA's own play-by-play sequence (PlayByPlayV3 actionId) for a random sample of
games where the two orderings disagree. Note: for events in the same second the
NBA sequence also just follows logging order, so this checks agreement with the
NBA's sequence rather than proving what happened on court.

Run from the project root (after clean.py):  .venv/bin/python pipeline/check_order.py 2025-26 [more seasons] [--games 10]
"""

import argparse
import json
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import playbyplayv3

from download import PAUSE_SECONDS

PBP_DIR = Path("data/raw/pbp")


def play_by_play(game_id):
    """Cached play-by-play for one game."""
    path = PBP_DIR / f"{game_id}.json"
    if not path.exists():
        time.sleep(PAUSE_SECONDS)
        raw = playbyplayv3.PlayByPlayV3(game_id=game_id, timeout=60).get_dict()
        PBP_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(raw))
    return json.loads(path.read_text())


def true_rank(game_id):
    """Map GAME_EVENT_ID -> position in the play-by-play's true sequence."""
    actions = play_by_play(game_id)["game"]["actions"]
    shots = [a for a in actions if a["isFieldGoal"] == 1]
    # actionId is the NBA's sequence; a shot's actionNumber is its GAME_EVENT_ID
    return {a["actionNumber"]: a["actionId"] for a in shots}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("seasons", nargs="*", default=["2025-26"])
    parser.add_argument("--games", type=int, default=10, help="games to sample per season")
    args = parser.parse_args()
    for season in args.seasons:
        check_season(season, args.games)


def check_season(season, n_games):
    shots = pd.read_parquet(f"data/interim/shots_{season}.parquet")
    by_event_id = shots.sort_values(["PLAYER_ID", "GAME_ID", "GAME_EVENT_ID"])
    flagged = by_event_id.groupby(["PLAYER_ID", "GAME_ID"])["ELAPSED_SECONDS"].diff() < 0
    disagree_games = by_event_id.loc[flagged, "GAME_ID"].drop_duplicates()
    sample = disagree_games.sample(min(n_games, len(disagree_games)), random_state=1)

    results = {"GAME_EVENT_ID": 0, "clock (ties: GAME_EVENT_ID)": 0}
    n_player_games = skipped = 0
    for game_id in sorted(sample):
        game = shots[shots["GAME_ID"] == game_id].copy()
        rank = true_rank(game_id)
        game["TRUE_RANK"] = game["GAME_EVENT_ID"].map(rank)
        # Skip player-games with a shot the play-by-play doesn't list
        incomplete = game.groupby("PLAYER_ID")["TRUE_RANK"].transform(lambda r: r.isna().any())
        skipped += game.loc[incomplete, "PLAYER_ID"].nunique()
        game = game[~incomplete]

        for _, pg in game.groupby("PLAYER_ID"):
            truth = list(pg.sort_values("TRUE_RANK")["GAME_EVENT_ID"])
            orders = {
                "GAME_EVENT_ID": list(pg.sort_values("GAME_EVENT_ID")["GAME_EVENT_ID"]),
                "clock (ties: GAME_EVENT_ID)": list(
                    pg.sort_values(["ELAPSED_SECONDS", "GAME_EVENT_ID"])["GAME_EVENT_ID"]
                ),
            }
            n_player_games += 1
            for name, order in orders.items():
                results[name] += order == truth

    print(f"{season}: {len(sample)} sampled games with disagreements, {n_player_games} player-games"
          f" ({skipped} skipped: shot missing from play-by-play)")
    for name, correct in results.items():
        print(f"  ordered by {name:<28}: {correct}/{n_player_games} player-games match the play-by-play")


if __name__ == "__main__":
    main()
