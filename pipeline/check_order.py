"""Which shot order is right: GAME_EVENT_ID or the game clock?

GAME_EVENT_ID turned out to be the order events were typed in, so shots logged
late get a too-high id (DECISIONS.md). This script checks both orderings against
the play-by-play feed (PlayByPlayV3), whose actionId follows the true sequence,
for a random sample of games where the two orderings disagree.

Run from the project root (after clean.py):  .venv/bin/python pipeline/check_order.py 2025-26
"""

import argparse
import json
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import playbyplayv3

from download import PAUSE_SECONDS

PBP_DIR = Path("data/raw/pbp")
SAMPLE_GAMES = 10


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
    # actionId is the true order; a shot's actionNumber is its GAME_EVENT_ID
    return {a["actionNumber"]: a["actionId"] for a in shots}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("season", nargs="?", default="2025-26")
    season = parser.parse_args().season

    shots = pd.read_parquet(f"data/interim/shots_{season}.parquet")
    by_event_id = shots.sort_values(["PLAYER_ID", "GAME_ID", "GAME_EVENT_ID"])
    flagged = by_event_id.groupby(["PLAYER_ID", "GAME_ID"])["ELAPSED_SECONDS"].diff() < 0
    disagree_games = by_event_id.loc[flagged, "GAME_ID"].drop_duplicates()
    sample = disagree_games.sample(min(SAMPLE_GAMES, len(disagree_games)), random_state=1)

    results = {"GAME_EVENT_ID": 0, "clock (ties: GAME_EVENT_ID)": 0}
    n_player_games = 0
    for game_id in sorted(sample):
        game = shots[shots["GAME_ID"] == game_id].copy()
        rank = true_rank(game_id)
        game["TRUE_RANK"] = game["GAME_EVENT_ID"].map(rank)
        assert game["TRUE_RANK"].notna().all(), f"{game_id}: shot missing from play-by-play"

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

    print(f"{len(sample)} sampled games with disagreements, {n_player_games} player-games")
    for name, correct in results.items():
        print(f"  ordered by {name:<28}: {correct}/{n_player_games} player-games match the play-by-play")


if __name__ == "__main__":
    main()
