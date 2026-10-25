# Is the Hot Hand Real? — Agreed plan

Agreed with the user on 2026-10-25. This file is the source of truth for scope; DECISIONS.md records each choice as it is made.

## Goal
A website where anyone can search an NBA player and see whether their shooting streaks are statistically distinguishable from luck, across their career (as far back as the data goes), with honest effect sizes and uncertainty.

The question: does a player's chance of making a shot go up after they've made their previous shots?

## Data
- Source: `nba_api` → `ShotChartDetail` with `player_id=0, team_id=0, context_measure_simple="FGA"`, regular season, 1996-97 through 2025-26, requested in monthly date-range chunks (the API caps a response at 102,400 rows, about half a season; see DECISIONS.md 2026-10-25). Any chunk returning exactly 102,400 rows is treated as truncated and fails the download. Shot-chart data does not exist before 1996-97, so careers that started earlier are partial; say so on those player pages.
- Fields used: GAME_ID, GAME_EVENT_ID, PLAYER_ID, PLAYER_NAME, TEAM_ID, PERIOD, MINUTES_REMAINING, SECONDS_REMAINING, SHOT_MADE_FLAG, SHOT_DISTANCE, SHOT_ZONE_BASIC, SHOT_ZONE_AREA, LOC_X, LOC_Y, ACTION_TYPE, SHOT_TYPE.
- Downloads run locally (stats.nba.com blocks most cloud IPs). Throttle (a few seconds between calls), retry with exponential backoff, browser-like headers, cache every raw response in `data/raw/` (git-ignored) and never re-download a cached season.
- First step: a single-request feasibility probe. If nba_api is not workable, stop and propose alternatives (Kaggle/GitHub shot datasets, PlayByPlayV3) with their licences before proceeding.
- Shot order within a game: sort by game clock (period + time remaining), ties broken by GAME_EVENT_ID. GAME_EVENT_ID alone is the order events were typed in and misplaces shots logged late (changed 2026-10-25, see DECISIONS.md). Flag the shots that GAME_EVENT_ID order would misplace; run `pipeline/check_order.py` against play-by-play for every season (older seasons especially).
- Terms: data belongs to the NBA (NBA.com terms: personal, non-commercial use). The user should read them. Attribution on every page: "Data: NBA.com Stats via nba_api. Not affiliated with or endorsed by the NBA." Commit processed outputs only, never raw dumps.

## Statistics
For each player, k = 1, 2, 3:
1. D_k = P̂(make | previous k shots in the same game all makes) − P̂(make | previous k all misses), counts pooled across games. Streaks never cross games.
2. Null: permute outcomes within each game (B = 10,000). This fixes each game's make count, so it tests within-game sequential dependence only (explain on the Method page). The null mean is the bias of the raw comparison, and it can have either sign: the Miller & Sanjurjo bias (negative, large in a single short sequence, small once games are pooled) plus the effect of pooling good and bad nights (positive, usually larger in game data). Subtracting it removes both (simulations, DECISIONS.md 2026-10-25). If a player's p-value is small, run extra shuffles so BH can resolve it (p-values can't go below 1/(B+1)).
3. Effect size = D_obs − mean(D_null), in percentage points.
4. p-value: two-sided, measured from the null mean, (b+1)/(B+1).
5. 95% CI: game-level percentile bootstrap of the bias-corrected effect, re-estimating the bias in every bootstrap sample (B_boot = 2,000, bias from 1,000 saved shuffles). Measured coverage ≈ 94% with 40 games per player (DECISIONS.md).
6. Descriptive panel: FG% overall and after 1/2/3 makes/misses with Wilson CIs, clearly labelled as raw/uncorrected.
7. Headline k = 3 (matches Gilovich et al. 1985 and Miller & Sanjurjo 2018); k = 1, 2 shown alongside. BH-FDR across players, separately per k.
8. Career level is the main test (all career games pooled, permuting within games). Per-season effects shown as estimate + CI only (descriptive, no significance flags), to avoid multiplying tests.
9. Minimum 300 career FGA to run the test and enter the FDR family; every player stays searchable, those below the threshold show basic stats and "not enough shots for a reliable test".
10. League-wide pooled estimate: shot-weighted mean of per-player effects; null by combining permutation draw b across players. Per season and all-time.
11. Wording: effect sizes and uncertainty; "no detectable effect", never "no hot hand".
12. Limitations to state in the UI: shot difficulty (control for distance/zone later); putbacks/tip-ins follow misses and go in often (sensitivity analysis later); missed shots on shooting fouls are not recorded as FGA.

Tests (pytest): hand-built sequences (incl. streaks that would wrongly cross games); naive D_k biased down in one long sequence and biased up with good/bad nights, while the corrected effect ≈ 0 in both; false-positive rate ≈ 5% at α = 0.05 (3.8–6.2% over 2,000 sims, all k); CI coverage ≈ 95% (≥ 92.5% over 2,000 sims); simulated hot-hand shooters detected, plus a power curve by shot count and effect size; simulated i.i.d. league → ≈ 0 BH discoveries.

## Architecture
- `pipeline/` Python (pandas, numpy, scipy, statsmodels, nba_api, matplotlib): download → clean → stats → build_json (one JSON per player, `index.json`, `league.json`).
- `site/` Vite + plain TypeScript + Observable Plot, hash routing (`#/player/<id>`), accent-insensitive search over `index.json`, colour-blind-safe palette, text alternatives for charts.
- Hosting: GitHub Pages via a GitHub Action (confirmed, see DECISIONS.md).
- Python env: plain `venv` + `requirements.txt`.

Pages: Home (league result + search), Player (career + per-season analysis, conditional FG% with CIs, streak visual, null distribution with observed value, plain-English summary with caveats), Method (GVT 1985, Miller & Sanjurjo 2018), About (sources, limitations, attribution).

## Milestones (stop after each and show the user how to run it and what to check)
1. MVP: 2025-26 regular season, every player (changed from 5 star players on 2026-10-25, see DECISIONS.md). Feasibility probe, download, clean, stats, tests, power curve, matplotlib plots. The 284 players with ≥ 300 FGA get the full test with BH-FDR across them; the rest get basic stats only. Includes the 2025-26 league-wide pooled estimate.
2. Static site with player pages for every 2025-26 player, plus search (too many players to list by hand).
3. Scale to all seasons 1996-97 → 2025-26 and every player: career + per-season analysis, search, league page with BH-FDR, Method and About pages, deploy.
4. Future ideas (don't build yet): playoffs vs regular season, shot-difficulty control (distance/zone), putback sensitivity analysis, player comparisons, shareable comparison links.
