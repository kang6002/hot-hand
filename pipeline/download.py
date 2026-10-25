"""Download every regular-season field-goal attempt for one season from nba_api.

The API returns at most 102,400 rows per request (about half a season), so we
ask for one calendar month at a time (see DECISIONS.md). Each month's raw JSON
is cached in data/raw/shotchart/<season>/<YYYY-MM>.json and never re-downloaded.

Run from the project root:  .venv/bin/python pipeline/download.py 2025-26
"""

import argparse
import calendar
import json
import time
from pathlib import Path

import requests
from nba_api.stats.endpoints import shotchartdetail

RAW_DIR = Path("data/raw/shotchart")
ROW_CAP = 102_400      # server limit found by pipeline/probe.py
PAUSE_SECONDS = 3      # wait between requests, to be polite to stats.nba.com
MAX_ATTEMPTS = 5       # retries wait 5, 10, 20, 40 s (exponential backoff)


class TruncatedResponse(Exception):
    """A response hit the row cap, so some shots are missing."""


def month_ranges(season):
    """Months to request for a season like "2025-26": October to August.

    Wider than any regular season (the 2020 bubble ran into August, 2020-21
    started in December); months with no games simply return zero rows.
    Returns (label, first_day, last_day) with dates as MM/DD/YYYY.
    """
    start_year = int(season[:4])
    months = [(start_year, m) for m in range(10, 13)]
    months += [(start_year + 1, m) for m in range(1, 9)]
    ranges = []
    for year, month in months:
        last_day = calendar.monthrange(year, month)[1]
        ranges.append((
            f"{year}-{month:02d}",
            f"{month:02d}/01/{year}",
            f"{month:02d}/{last_day:02d}/{year}",
        ))
    return ranges


def shot_rows(raw):
    """Return (headers, rows) of the Shot_Chart_Detail table in a raw response."""
    table = next(r for r in raw["resultSets"] if r["name"] == "Shot_Chart_Detail")
    return table["headers"], table["rowSet"]


def request_month(season, date_from, date_to):
    """One API request, retried with exponential backoff on network errors."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            endpoint = shotchartdetail.ShotChartDetail(
                team_id=0,
                player_id=0,
                context_measure_simple="FGA",
                season_nullable=season,
                season_type_all_star="Regular Season",
                date_from_nullable=date_from,
                date_to_nullable=date_to,
                timeout=90,
            )
            raw = endpoint.get_dict()
            shot_rows(raw)  # fails here if the response isn't the expected shape
            return raw
        except (requests.RequestException, ValueError, KeyError, StopIteration) as err:
            if attempt == MAX_ATTEMPTS:
                raise
            wait = 5 * 2 ** (attempt - 1)
            print(f"    attempt {attempt} failed ({type(err).__name__}); retrying in {wait} s")
            time.sleep(wait)


def download_season(season):
    """Download (or load from cache) every month of a season; return all raw responses."""
    season_dir = RAW_DIR / season
    season_dir.mkdir(parents=True, exist_ok=True)
    responses = []
    for label, date_from, date_to in month_ranges(season):
        path = season_dir / f"{label}.json"
        if path.exists():
            raw = json.loads(path.read_text())
            print(f"  {label}: cached, {len(shot_rows(raw)[1]):,} shots")
        else:
            time.sleep(PAUSE_SECONDS)
            raw = request_month(season, date_from, date_to)
            n = len(shot_rows(raw)[1])
            if n >= ROW_CAP:
                raise TruncatedResponse(f"{season} {label}: {n:,} rows = row cap; split this month further")
            # Write to a temporary file first so an interrupted run never leaves a half-written cache file
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(raw))
            tmp.rename(path)
            print(f"  {label}: downloaded, {n:,} shots")
        responses.append(raw)
    return responses


def summarise(season, responses):
    """Print checks that the season is complete and has no duplicate shots."""
    headers = shot_rows(responses[0])[0]
    rows = [row for raw in responses for row in shot_rows(raw)[1]]
    col = {name: i for i, name in enumerate(headers)}

    shot_keys = {(r[col["GAME_ID"]], r[col["GAME_EVENT_ID"]]) for r in rows}
    games = {r[col["GAME_ID"]] for r in rows}
    dates = sorted(r[col["GAME_DATE"]] for r in rows)

    print(f"\n{season}: {len(rows):,} shots, {len(games):,} games, {dates[0]} to {dates[-1]}")
    print(f"Duplicate shots (same game + event id): {len(rows) - len(shot_keys)}")

    # Regular-season game ids run 002YY00001, 002YY00002, ...; list any gaps
    numbers = sorted(int(g[-5:]) for g in games)
    missing = sorted(set(range(1, numbers[-1] + 1)) - set(numbers))
    print(f"Highest game number: {numbers[-1]}; missing game numbers: {missing or 'none'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("season", nargs="?", default="2025-26", help='e.g. "2025-26"')
    season = parser.parse_args().season
    print(f"Season {season}")
    summarise(season, download_season(season))


if __name__ == "__main__":
    main()
