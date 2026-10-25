import pandas as pd

from clean import KEEP, clean, elapsed_seconds


def test_elapsed_seconds_regulation_and_overtime():
    period = pd.Series([1, 1, 4, 5, 6])
    minutes = pd.Series([12, 0, 0, 5, 0])
    seconds = pd.Series([0, 0, 0, 0, 0])
    # tip-off, end of Q1, end of Q4, start of OT1, end of OT2
    assert list(elapsed_seconds(period, minutes, seconds)) == [0, 720, 2880, 2880, 3480]


def raw_shots(rows):
    """Minimal raw DataFrame: rows are (game, event_id, player, period, min, sec, made)."""
    df = pd.DataFrame(rows, columns=["GAME_ID", "GAME_EVENT_ID", "PLAYER_ID", "PERIOD",
                                     "MINUTES_REMAINING", "SECONDS_REMAINING", "SHOT_MADE_FLAG"])
    for col in KEEP:
        if col not in df:
            df[col] = "x" if col != "GAME_DATE" else "20251021"
    df["SHOT_ATTEMPTED_FLAG"] = 1
    df["EVENT_TYPE"] = df["SHOT_MADE_FLAG"].map({1: "Made Shot", 0: "Missed Shot"})
    return df


def test_late_logged_shot_is_put_back_in_clock_order():
    # Event 90 happened at 10:00 but was typed in late, after event 20 (8:00)
    raw = raw_shots([
        ("g1", 10, "p1", 1, 11, 0, 1),
        ("g1", 20, "p1", 1, 8, 0, 0),
        ("g1", 90, "p1", 1, 10, 0, 1),
    ])
    shots = clean(raw, "2025-26")
    assert list(shots["GAME_EVENT_ID"]) == [10, 90, 20]
    assert list(shots["SHOT_NUMBER"]) == [1, 2, 3]
    assert list(shots["EVENT_ID_OUT_OF_ORDER"]) == [False, True, False]


def test_same_second_shots_keep_event_id_order():
    # Missed shot and tip-in in the same second: lower event id first
    raw = raw_shots([
        ("g1", 31, "p1", 2, 5, 3, 1),
        ("g1", 30, "p1", 2, 5, 3, 0),
    ])
    assert list(clean(raw, "2025-26")["GAME_EVENT_ID"]) == [30, 31]


def test_shot_number_restarts_each_game_and_player():
    raw = raw_shots([
        ("g1", 1, "p1", 1, 11, 0, 1),
        ("g1", 2, "p2", 1, 10, 0, 1),
        ("g1", 3, "p1", 1, 9, 0, 0),
        ("g2", 1, "p1", 1, 11, 0, 0),
    ])
    shots = clean(raw, "2025-26")
    assert list(shots[["PLAYER_ID", "GAME_ID", "SHOT_NUMBER"]].itertuples(index=False, name=None)) == [
        ("p1", "g1", 1), ("p1", "g1", 2), ("p1", "g2", 1), ("p2", "g1", 1),
    ]
