"""Write the static JSON files the website reads (careers 1996-97 to 2025-26).

Run from the project root (after analyse.py career, analyse.py seasons all, player_info.py):
  .venv/bin/python pipeline/build_json.py
Outputs in site/public/data/:
  index.json              every player (for search)
  league.json             all-time and per-season league results, power curve, sensitivity check
  league_players.json     every tested player's career effect (league page chart)
  players/<id>.json       career: raw FG%, test results, shuffle histograms; per-season estimates
  shots/<id>.json         every shot, by season and game (loaded only when opened)
"""

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from analyse import FDR_Q, INTERIM_DIR, MIN_FGA, PROCESSED_DIR, load_shots
from download import FIRST_SEASON, all_seasons
from stats import KS

SITE_DATA = Path("site/public/data")
HIST_BINS = 40
ATTRIBUTION = "Data: NBA.com Stats via nba_api. Not affiliated with or endorsed by the NBA."
SENSITIVITY_SEASON = "2025-26"


def num(x, digits=4):
    """JSON-safe rounded number (NaN -> null)."""
    if x is None or pd.isna(x):
        return None
    return round(float(x), digits)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False))


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


def league_rows(league):
    rows = []
    for r in league.itertuples():
        row = {"k": int(r.k), "n_players": int(r.n_players), "effect": num(r.effect),
               "ci_low": num(r.ci_low), "ci_high": num(r.ci_high), "p_value": num(r.p_value, 6)}
        if hasattr(r, "discoveries_hot"):
            row |= {"discoveries_hot": int(r.discoveries_hot), "discoveries_cold": int(r.discoveries_cold)}
        if hasattr(r, "season"):
            row["season"] = r.season
        rows.append(row)
    return rows


def career_test(r, null_draws):
    return {
        "d_raw": num(r["d_raw"]), "bias": num(r["bias"]), "effect": num(r["effect"]),
        "ci_low": num(r["ci_low"]), "ci_high": num(r["ci_high"]),
        "p_value": num(r["p_value"], 8), "q_value": num(r["q_value"], 4),
        "discovery": str(r["discovery"]) == "True",
        "n_shuffles": int(r["n_shuffles"]),
        "null_hist": histogram(null_draws),
    }


def shot_log(shots):
    """{player_id: [{season, games: [{d: "MM-DD", s: "1011"}]}]}, games in date order."""
    per_game = (shots.groupby(["PLAYER_ID", "SEASON", "GAME_ID"], sort=False)
                .agg(date=("GAME_DATE", "first"),
                     s=("SHOT_MADE_FLAG", lambda x: "".join(map(str, x)))))
    per_game = per_game.reset_index().sort_values(["PLAYER_ID", "date"])
    per_game["d"] = per_game["date"].dt.strftime("%m-%d")
    logs = {}
    for (pid, season), g in per_game.groupby(["PLAYER_ID", "SEASON"], sort=False):
        logs.setdefault(int(pid), []).append({"season": season, "games": g[["d", "s"]].to_dict("records")})
    return logs


def main():
    career = PROCESSED_DIR / "career"
    players = pd.read_csv(career / "players.csv")
    streaks = pd.read_csv(career / "streaks.csv")
    league = pd.read_csv(career / "league.csv")
    draws = np.load(INTERIM_DIR / "draws_career.npz")
    draw_row = {int(pid): i for i, pid in enumerate(draws["player_id"])}
    null_draws = {k: draws[f"null_k{k}"] for k in KS}

    seasons_dir = PROCESSED_DIR / "seasons"
    s_players = pd.read_csv(seasons_dir / "players.csv")
    s_streaks = pd.read_csv(seasons_dir / "streaks.csv")
    s_league = pd.read_csv(seasons_dir / "league.csv")

    # Current names (shot data can carry old ones) and whether the career began before 1996-97
    info = pd.read_csv(PROCESSED_DIR / "player_info.csv").set_index("player_id")
    order = {s: i for i, s in enumerate(all_seasons())}
    s_players["order"] = s_players["season"].map(order)
    span = s_players.groupby("player_id").agg(first=("order", "min"), last=("order", "max"), n=("order", "count"))
    season_label = all_seasons()

    def name_of(pid, fallback):
        return info.loc[pid, "name"] if pid in info.index else fallback

    def partial(pid):
        return bool(pid in info.index and info.loc[pid, "partial_career"])

    # Start from empty folders so removed players don't linger
    for sub in ("players", "shots"):
        if (SITE_DATA / sub).exists():
            shutil.rmtree(SITE_DATA / sub)

    print("Building shot logs ...")
    logs = shot_log(load_shots(all_seasons()))

    streaks_by_pid = dict(tuple(streaks.groupby("player_id")))
    s_players_by_pid = dict(tuple(s_players.groupby("player_id")))
    s_streaks_by_pid = dict(tuple(s_streaks.groupby("player_id")))

    print("Writing player files ...")
    for p in players.itertuples():
        pid = int(p.player_id)
        rows = streaks_by_pid[pid].set_index("k")
        tested = bool(p.tested)
        ks = []
        for k in KS:
            r = rows.loc[k]
            entry = {"k": k, "after_makes": proportion(r, "makes"), "after_misses": proportion(r, "misses")}
            if tested:
                entry["test"] = career_test(r, null_draws[k][draw_row[pid]])
            ks.append(entry)

        # Per season: estimate + CI only (no p-values, no significance labels; PLAN.md)
        seasons = []
        ss = s_streaks_by_pid[pid]
        for sr in s_players_by_pid[pid].sort_values("order").itertuples():
            entry = {"season": sr.season, "fga": int(sr.fga), "games": int(sr.games),
                     "fg_pct": num(sr.fg_pct), "tested": bool(sr.tested)}
            if sr.tested:
                t = ss[ss["season"] == sr.season].set_index("k")
                entry["ks"] = [{"k": k, "effect": num(t.loc[k, "effect"]), "ci_low": num(t.loc[k, "ci_low"]),
                                "ci_high": num(t.loc[k, "ci_high"])} for k in KS]
            seasons.append(entry)

        write(SITE_DATA / "players" / f"{pid}.json", {
            "id": pid, "name": name_of(pid, p.player_name),
            "first_season": season_label[span.loc[pid, "first"]],
            "last_season": season_label[span.loc[pid, "last"]],
            "n_seasons": int(span.loc[pid, "n"]), "partial_career": partial(pid),
            "data_start": season_label[0],
            "fga": int(p.fga), "games": int(p.games),
            "fg": {"pct": num(p.fg_pct), "ci_low": num(p.fg_ci_low), "ci_high": num(p.fg_ci_high)},
            "tested": tested, "min_fga": MIN_FGA, "fdr_q": FDR_Q,
            "ks": ks, "seasons": seasons,
            "attribution": ATTRIBUTION,
        })
        write(SITE_DATA / "shots" / f"{pid}.json", logs[pid])

    index = sorted(
        ({"id": int(p.player_id), "name": name_of(int(p.player_id), p.player_name), "fga": int(p.fga),
          "tested": bool(p.tested), "first": season_label[span.loc[p.player_id, "first"]],
          "last": season_label[span.loc[p.player_id, "last"]]}
         for p in players.itertuples()),
        key=lambda x: x["name"])
    write(SITE_DATA / "index.json", {"players": index})

    fga = players.set_index("player_id")["fga"]
    tested_rows = streaks[streaks["p_value"].notna()]
    write(SITE_DATA / "league_players.json", [
        {"id": int(r.player_id), "name": name_of(int(r.player_id), ""), "fga": int(fga[r.player_id]),
         "k": int(r.k), "effect": num(r.effect), "ci_low": num(r.ci_low), "ci_high": num(r.ci_high),
         "q_value": num(r.q_value), "discovery": str(r.discovery) == "True"}
        for r in tested_rows.itertuples()])

    write(SITE_DATA / "league.json", {
        "first_season": season_label[0], "last_season": season_label[-1],
        "min_fga": MIN_FGA, "fdr_q": FDR_Q,
        "n_players": int(len(players)), "n_tested": int(players["tested"].sum()),
        "n_shots": int(players["fga"].sum()),
        "ks": league_rows(league),
        "seasons": league_rows(s_league),
        "power": power_rows(),
        # Putback check (one season): the same season's main result and the result without putbacks
        "putback_check": {
            "season": SENSITIVITY_SEASON,
            "main": sensitivity_rows(PROCESSED_DIR / SENSITIVITY_SEASON / "league.csv"),
            "without": sensitivity_rows(PROCESSED_DIR / SENSITIVITY_SEASON / "sensitivity_no_putbacks" / "league.csv"),
        },
        "attribution": ATTRIBUTION,
    })

    size = sum(f.stat().st_size for f in SITE_DATA.rglob("*.json"))
    print(f"Wrote {len(players)} players (+ shot logs), index and league files to {SITE_DATA} ({size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
