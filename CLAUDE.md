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
- 2026-10-25: Milestone 1 complete (waiting for user OK): every 2025-26 player (284 tested, ≥ 300 FGA); pipeline download → clean → analyse → power → plots; outputs in `data/processed/` and `figures/`. Result: no BH discoveries; league effect −1.0 / −1.3 / −2.0 pp (k = 1/2/3), likely shot selection + putbacks (not yet controlled); power is low per player-season (see DECISIONS.md). Open: putback check now or keep in Milestone 4? Next: Milestone 2 (static site).
- Hosting: GitHub Pages (user has a GitHub account). Repo not yet pushed to GitHub; do that when we deploy.
