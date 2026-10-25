# Is the Hot Hand Real?

NBA hot-hand website: Python pipeline → static JSON → static site (Vite + TypeScript + Observable Plot).

- Scope, statistical spec and milestones: see PLAN.md (agreed with the user; don't re-litigate).
- Log every non-trivial choice in DECISIONS.md (what, why, alternatives).

## Working with the user
- Second-year biology student, comfortable with Python and R, new to web development.
- Work in small steps and briefly explain each choice; the user must be able to explain every decision in a hackathon application. Relate web concepts to R/Python where it helps (e.g. Observable Plot ≈ ggplot2).
- Stop at the end of each milestone: show results, explain how to run it and what to check, and wait for OK.

## Rules
- Never use the naive streak comparison uncorrected; see PLAN.md § Statistics.
- Wording: "no detectable effect", never "no hot hand".
- Raw API responses go in `data/raw/` (git-ignored); commit processed outputs only.
- Downloads run locally, throttled, with retries and caching.

## Status
- 2026-10-25: Milestone 1 done (commit a822c7c): every 2025-26 player (284 tested, ≥ 300 FGA). Result: no BH discoveries; league effect −1.0 / −1.3 / −2.0 pp (k = 1/2/3), likely shot selection (not yet controlled); power is low per player-season (see DECISIONS.md).
- 2026-10-25: Milestone 2 done (commit bbb3872): static site in `site/` (home + all 582 player pages, search, Vitest tests), data from `pipeline/build_json.py`.
- 2026-10-25: Putback check done (commit ee69cbe). Milestone 3 complete locally (not yet committed or published): 30 seasons, career test for 1,676 players (0 hot; 19/7/0 cold for k = 1/2/3; league −1.1 to −1.2 pp), per-season estimates, site with League/Method/About pages, README, MIT licence, deploy workflow.
- Publishing: user chose public repo `kang6002/hot-hand`, commit identity "Kang Rui Li" + GitHub noreply email, MIT, read NBA terms. `gh` installed in `~/.local/gh` and logged in. Waiting for the user's "OK to publish" after checking the local preview.
- Next idea (Milestone 4): shot-difficulty control (distance/zone), the most likely explanation of the negative effect.

## How to run
- Python: `.venv/bin/python pipeline/<step>.py 2025-26`, in order download → clean → analyse → power → plots → build_json; tests `.venv/bin/python -m pytest` (slow ones: `-m slow`).
- Node lives in `~/.local/node` (installed without admin): `export PATH="$HOME/.local/node/bin:$PATH"`, then in `site/`: `npm run dev` (local site), `npm test`, `npm run build`.
