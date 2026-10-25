# Decisions log

Each entry: what we chose, why, and the alternatives considered.

## 2026-10-25 — Separate repository
- **Chose:** a standalone repo at `~/projects/hot-hand`.
- **Why:** unrelated to any other project; keeps history, dependencies and Claude Code context separate.
- **Alternatives:** a subfolder of an existing repo (mixes unrelated work).

## 2026-10-25 — Bias-corrected permutation test, not the naive comparison
- **Chose:** shuffle each player's outcomes within each game; effect = observed difference − mean of the shuffled differences; two-sided p-value; game-level bootstrap CI.
- **Why:** the naive P(make | k makes) − P(make | k misses) is biased downward in finite sequences (Miller & Sanjurjo, 2018); in pooled game data it is mostly biased *upward* by good and bad nights (see "What the shuffle correction removes" below). The shuffled null reproduces that bias exactly, so subtracting its mean removes it. Shuffling within games keeps each game's make count fixed, so a player simply having a good night isn't counted as a hot hand.
- **Alternatives:** naive comparison (biased); analytic bias formulas (only exact for simple cases); logistic regression on previous outcomes (good later, when adding shot-difficulty controls).

## 2026-10-25 — Headline k = 3, two-sided tests
- **Chose:** k = 3 as the headline; k = 1, 2 shown alongside; BH-FDR applied separately for each k; two-sided tests.
- **Why:** k = 3 matches Gilovich, Vallone & Tversky (1985) and Miller & Sanjurjo (2018), so results are comparable. Two-sided lets a "cold hand" show up too.
- **Alternatives:** k = 1 (more data, more power, but a single make isn't really a "streak"); one-sided tests (more power for hot-hand effects, but can't detect the opposite).
- **Cost:** k = 3 has far fewer qualifying shots, so lower power; the power curve will quantify this.

## 2026-10-25 — Many seasons, career-level analysis
- **Chose:** all regular seasons with shot-chart data (1996-97 → 2025-26). The main test pools each player's whole career (still shuffling within games); per-season results are shown as estimates with CIs only.
- **Why:** more shots means more statistical power, especially for k = 3. Testing every player-season would multiply the number of tests about 5×, making FDR correction much harsher.
- **Alternatives:** a single season (low power, fewer players); significance flags per season (multiple-testing problem).
- **Caveats:** no shot-level data before 1996-97, so earlier careers are partial; older seasons need data-quality checks. Build and validate on one season first (Milestone 1), then scale (Milestone 3).

## 2026-10-25 — Every player searchable, test only with 300+ FGA
- **Chose:** every player gets a page. The test runs, and the player enters the FDR family, only with ≥ 300 career FGA.
- **Why:** the user wants a searchable database; below about 300 attempts the test has too little power to say anything useful.
- **Alternatives:** hide low-volume players (less complete); test everyone (many noisy, uninformative results that also dilute FDR).

## 2026-10-25 — Hosting on GitHub Pages
- **Chose:** GitHub Pages, deployed automatically by a GitHub Action whenever the site changes (set up in Milestone 2–3). The repo will need to be public.
- **Why:** free, the user already has a GitHub account, and the code and the live site sit in one place for judges.
- **Alternatives:** Vercel or Netlify (also free, but another account and service to explain); running our own server (unnecessary, since the site is just static files).

## 2026-10-25 — Python environment: venv with pinned versions
- **Chose:** a project-local `.venv` and a `requirements.txt` with exact versions (nba_api 1.12.0, pandas 3.1.0, numpy 2.5.4, scipy 1.18.1, statsmodels 0.15.0, matplotlib 3.11.2, pytest 9.1.1) on Python 3.13.
- **Why:** anyone (or a judge) can recreate the same environment and get the same numbers; similar to `renv` in R.
- **Alternatives:** unpinned requirements (results can silently change when packages update); conda or uv (more tooling than this project needs).

## 2026-10-25 — Download each season in monthly chunks (API row cap)
- **Found:** the feasibility probe (`pipeline/probe.py`) asked for the whole 2025-26 regular season in one request and got exactly 102,400 rows. Rows stopped at 29 Jan 2026, partway through the 4th quarter of game 0022500573. A full season is roughly 1,230 games × ~178 FGA ≈ 220,000 shots. A second request for March 2026 only returned 42,163 rows covering 239 complete games, so the server caps each response at 102,400 rows.
- **Chose:** request each season month by month with `date_from`/`date_to` (about 7 requests per season, roughly 210 in total). Any chunk with exactly 102,400 rows is treated as truncated and stops the download. After downloading, check the season's game count against the expected number.
- **Why:** a month is about 40,000 shots, comfortably under the cap. Date ranges also handle unusual seasons (1998-99 and 2011-12 lockouts, the 2019-20 bubble, 2020-21) without special cases.
- **Alternatives:** one request per team (30 per season, about 900 in total, so slower, and each shot is tied to the shooter's team, which complicates de-duplication); one request per player (thousands of requests); a third-party dataset (licence and provenance less clear, and the plan prefers nba_api while it works).

## 2026-10-25 — Download window and completeness checks
- **Chose:** request every season over the same fixed window, October to August (11 monthly requests, empty months return 0 rows). Each month is cached as `data/raw/shotchart/<season>/<YYYY-MM>.json`, written to a temporary file first and then renamed, so an interrupted run never leaves a half-written file. After each season we check: no duplicate (GAME_ID, GAME_EVENT_ID) pairs, and no gaps in the game numbers (regular-season ids run 002YY00001, 002YY00002, …).
- **Why:** one rule covers every season, including the 2019-20 bubble (finished in August) and 2020-21 (started in December), so we don't need a hand-made season calendar. The empty months cost about 4 extra requests per season (about 2 minutes over 30 seasons). The checks would catch a missing or doubled month.
- **Result for 2025-26:** 219,160 shots, 1,230 games (21 Oct 2025 – 12 Apr 2026), no duplicates, no missing game numbers.
- **Alternatives:** look up each season's exact start and end dates (fewer requests, but a hand-made list that is easy to get wrong).

## 2026-10-25 — Milestone 1 covers every player, not 5 stars
- **Chose (user's request):** analyse every player in 2025-26. The 284 players with ≥ 300 FGA (85% of all shots) get the full permutation test, with BH-FDR across those 284 for each k. The other 298 players get basic stats only, the same rule the plan already uses for careers. The 2025-26 league-wide pooled estimate also moves into Milestone 1.
- **Why:** the user wants as many players as can be tested meaningfully. The 300-FGA threshold already defines "meaningfully". Running BH-FDR on a real family of hundreds of players exercises the multiple-testing part of the method early, instead of first doing it in Milestone 3.
- **Alternatives:** 5 star players (the original plan: quicker to check by hand, but no multiple-testing family); a lower threshold such as 100 FGA (427 players, but very low power, especially for k = 3).
- **Caveat:** one season with 300–1,000 shots gives low power for k = 3. The power curve (later in Milestone 1) will show which effect sizes are detectable at these shot counts. Career pooling in Milestone 3 adds power.
- **Knock-on:** Milestone 2 now needs search, since there are too many players to list by hand.

## 2026-10-25 — Save cleaned shots as parquet (adds pyarrow)
- **Chose:** `data/interim/shots_<season>.parquet` (git-ignored), written with pyarrow 26.0.0.
- **Why:** keeps column types (GAME_ID stays text with its leading zeros, dates stay dates), much smaller and faster than CSV, and R reads it with `arrow::read_parquet`.
- **Alternatives:** CSV (types are lost and must be re-parsed; large for 30 seasons); pickle (Python-only, not safe to share).

## 2026-10-25 — Order shots by game clock, not GAME_EVENT_ID
- **Found:** the cleaning cross-check showed that in 2025-26, 620 shots (0.28%, in 605 player-games) are placed earlier by the game clock than GAME_EVENT_ID puts them. Two cases checked by hand against the play-by-play feed (PlayByPlayV3) showed GAME_EVENT_ID is the order events were *typed in*: a shot logged late gets a high id (e.g. a LeBron tip-in at 11:32 of Q3 had id 388, between events 341 and 389). The play-by-play's own sequence (`actionId`) and the clock were right.
- **Validated:** `pipeline/check_order.py` compared both orderings with the play-by-play for 10 random games that contain disagreements (202 player-games). Clock order matched in 202/202 player-games; GAME_EVENT_ID order matched in 192/202 (the 10 misses are exactly the flagged player-games).
- **Chose:** order each player's shots in a game by elapsed game time, ties broken by GAME_EVENT_ID. Keep a per-shot flag `EVENT_ID_OUT_OF_ORDER` so we can later show the results barely change if the flagged player-games are dropped.
- **Ties:** 272 shots share a second with another shot by the same player (136 groups). In 96% the first shot is a miss and the later one is almost always a tip-in or putback, so the GAME_EVENT_ID tie-break gives the right order.
- **Why it matters:** the whole analysis is about which shot came after which; a misplaced shot can create or break a streak.
- **Alternatives:** GAME_EVENT_ID order (the original plan; wrong for late-logged shots); the play-by-play's `actionId` for every game (exact, but one extra request per game, about 37,000 for all seasons, i.e. more than a day of throttled downloading); dropping flagged player-games (loses 2.4% of player-games for no gain).

## 2026-10-25 — What the shuffle correction removes (correcting our earlier explanation)
- **Found:** a test expecting the raw difference D_k to be clearly negative for simulated shooters with no hot hand failed. Simulations (400 shooters per setting, k = 3, no hot hand):
  - one 100-shot sequence, like Gilovich et al.'s shooting experiment: raw D_3 ≈ −8.6 pp (the Miller & Sanjurjo bias);
  - 70 games, same FG% every game: raw D_3 ≈ −1.3 pp (the bias mostly disappears when many games are pooled, because each game's make count also varies);
  - 70 games where FG% varies between games (sd 8 pp): raw D_3 ≈ **+6.1 pp**. On good nights more shots follow makes *and* more shots go in, so pooling games makes the raw comparison look like a hot hand.
  - After the within-game shuffle correction, all three average ≈ 0.
- **Consequence:** the method is unchanged. Our explanation changes: in NBA game data the shuffle mainly removes the upward bias from good and bad nights, plus the (smaller) Miller & Sanjurjo bias. A player's null mean can be positive or negative (in real 2025-26 data, Maxey −1.4 pp and Gobert +1.8 pp for k = 1). This goes on the Method page. It strengthens the rule never to show the raw comparison uncorrected.
- **Tests now check:** biased down in one long sequence, biased up with good and bad nights, and corrected ≈ 0 in both.
- **Real 2025-26 data (added after step 5):** across the 284 tested players the median bias is −0.7 / −1.7 / −3.1 pp for k = 1 / 2 / 3, so the Miller & Sanjurjo part dominates for most real players (their game-to-game variation is mostly ordinary luck); for some players it is positive. The bias must come from shuffling the player's own games, not from a fixed formula.

## 2026-10-25 — Confidence interval: re-estimate the bias in every bootstrap sample
- **Chose:** resample games with replacement (2,000 bootstrap samples). For each sample, compute both the raw D_k and its own bias. The bias is the average D_k over the same 1,000 within-game shuffles, using per-game streak counts saved from the main shuffle run, so it's one matrix multiplication rather than re-shuffling. The CI is the 2.5th and 97.5th percentiles of the bootstrap effects (a percentile interval).
- **Why:** the bias depends on which games are in the sample (good and bad nights), and it moves together with the raw D_k. Subtracting one fixed bias would give intervals of the wrong width.
- **Measured coverage** (simulations, 2,000 players each): ≈ 94% with 40 games per player, with or without a hot hand (94.4% and 94.9% in the test). The intervals are centred correctly; they're slightly too narrow, which is typical of a percentile bootstrap when there are few games to resample. Coverage approaches 95% with more games (80 games: 94–95.5%). Independent shuffles for the bootstrap made no difference (94.3% vs 93.6%, within noise).
- **Alternatives:** a fixed bias (wrong width); re-shuffling inside every bootstrap sample (2,000 × 1,000 shuffles per player, too slow); BCa or studentized bootstrap (more complex; would gain at most about 1 point of coverage). Revisit if real players with few games matter.

## 2026-10-25 — Test calibration checks
- **False-positive rate** (no hot hand, good and bad nights): 4,000 players gave 4.7–5.3% at α = 0.05 and ≈ 1% at α = 0.01 for every k, so the test is well calibrated. The slow test uses 2,000 players and requires 3.8–6.2% for all three k. This band is wide enough that a correct test passes for all three k together 95% of the time. The first version used the plan's band of 3.6–6.4% per k with 1,000 players; checking three k against a ±2 standard error band gives about a 14% chance of a false alarm, and one occurred (k = 1: 6.7%).
- **BH:** a league of 300 players with no hot hand and 10,000 shuffles each gave 0 discoveries for every k.
- **Slow tests** are marked `slow` and skipped by default (`pytest -m slow` runs them, about 2 minutes).

## 2026-10-25 — More shuffles for players with small p-values (to do in step 5)
- **Found:** with B shuffles the smallest possible p-value is 1/(B+1) ≈ 0.0001. For BH with m players, the strongest player is discovered only if p ≤ 0.05/m: 0.00018 for 284 players, 0.000025 for ~2,000 players (Milestone 3). With B = 10,000, a single genuinely hot player could barely or never be detected.
- **Plan:** run 10,000 shuffles for everyone, then add shuffles (up to 1,000,000) for players whose p-value is below about 0.01, so the p-value is precise enough for BH. This only affects a handful of players and takes seconds each.
- **Alternatives:** a normal approximation to the null (fast, but no longer exact); 1,000,000 shuffles for everyone (≈ 1 minute per player, hours in total).

## 2026-10-25 — Season run: extra shuffles, seeds, league estimate, outputs
- **Extra shuffles:** every tested player starts with 10,000 shuffles. If fewer than 100 shuffles (for any k) are as extreme as the real data, the player is rerun with 10× more shuffles, up to 1,000,000. Stopping at 100 extreme shuffles gives each p-value a relative precision of about ±10%, enough for BH. Rerunning only affects players with p < about 0.01.
- **Seeds:** each player's random numbers are seeded with (player id, number of shuffles), so every result can be reproduced exactly and doesn't depend on the order players are processed.
- **League-wide estimate (per k):** mean of the tested players' effects weighted by their FGA (PLAN.md). p-value: for each shuffle b, combine every player's shuffle-b deviation from their own null mean with the same weights; players are independent, so this is a draw from the league-wide null. **Added:** a 95% CI built the same way from each player's bootstrap draws (bootstrap sample b of every player combined). It describes these players in this season.
- **Outputs:** tidy CSVs (one row per observation, as in R's tidyverse) in `data/processed/<season>/`: `players.csv` (one row per player), `streaks.csv` (one row per player and k: raw FG% after makes/misses with Wilson CIs for everyone, test results for tested players), `league.csv` (one row per k). These are small, processed and committed. Shuffle and bootstrap draws for plots go to `data/interim/draws_<season>.npz` (git-ignored, regenerated by the script).
- **Alternatives:** one wide table (about 60 columns, hard to read); JSON now (the site format comes in Milestone 2, built from these tables).

## 2026-10-25 — Power curve: design and what it shows
- **Design** (`pipeline/power.py`): simulated shooters with base FG% 46%, mild good and bad nights (game sd 4 pp), 15 shots per game. Hot hand: after k makes in a row, the make probability rises by 0, 2, 5 or 10 pp (the same k is simulated and tested). 300 to 6,000 FGA (one season to a career). 200 players per scenario, 2,000 shuffles. Power is reported at α = 0.05 and at α = 0.001; the stricter level is roughly what BH needs to flag one player among hundreds. Scenarios run in parallel on all CPU cores (6 minutes).
- **Results** (power at α = 0.05 / α = 0.001):
  - k = 1, 1,500 FGA (a high-volume season): +10 pp → 94% / 57%; +5 pp → 39% / 7%; +2 pp → 8% / 0%.
  - k = 3, 1,500 FGA: +10 pp → 33% / 2%; +5 pp → 11% / 1%.
  - k = 3, 6,000 FGA (a long career): +10 pp → 87% / 39%; +5 pp → 31% / 5%.
  - With no hot hand, the detection rate stays at about α (2.5–6.5% at 0.05), as it should.
- **Meaning:** for single players in a single season, only very large hot hands (around 10 pp, mostly k = 1) can be detected, especially after the BH correction. Published estimates of the real effect are a few pp. So in 2025-26, "0 BH discoveries" is expected even if a modest hot hand exists. This is why the site must say "no detectable effect", never "no hot hand". It's also why careers (Milestone 3) and the league-wide estimate (which pools hundreds of players) matter.
- **Attenuation:** the estimated effect is smaller than the simulated rise (+10 pp → ≈ +8.6 pp for k = 1, ≈ +7 pp for k = 3), because shuffling within games also absorbs the part of a hot hand that shows up as a good night. The method is conservative: it understates a real hot hand rather than inventing one.
- **Not changed:** k = 3 stays the headline (agreed in the plan for comparability with Gilovich et al. 1985 and Miller & Sanjurjo 2018). The power curve quantifies its cost, and k = 1, 2 are shown alongside.

## 2026-10-25 — Milestone 1 figures (matplotlib)
- **Chose:** `pipeline/plots.py` writes PNGs to `figures/` (committed: small, and useful for the application). Figures:
  - `figures/power_curve.png`: power curve;
  - `figures/<season>/effects.png`: every tested player's effect with CI, plus the league estimate;
  - `figures/<season>/diagnostics.png`: p-value histograms and the bias distribution;
  - `figures/<season>/player_<name>.png`: a prototype of the player page (raw FG% after makes/misses with Wilson CIs, labelled "not bias-corrected"; shuffle distribution with the real value for each k).
- **Style:** colours from a validated reference data-viz palette, light mode. Ordered effect sizes use one blue ramp, light to dark. Hot/cold use the red ↔ blue pair (none needed this season). After makes/misses use categorical blue/orange. Lines are always identified by a legend plus direct labels where they fit. Every figure carries the NBA attribution. The palette validator needs Node.js, which isn't installed; the colours are the palette's documented, pre-validated steps.
- **Alternatives:** Observable Plot right away (that's the site, Milestone 2; matplotlib is quicker for checking results).

## 2026-10-25 — Hosting: GitHub Pages under the user's account
- **Chose (user confirmed):** GitHub Pages, account `kang6002`. Creating the repository and the deploy Action happen in Milestone 3, and only after the user OKs the repository name and visibility.
- **Why:** free and static (fits our "pipeline → JSON → static site" design), and gives the application a public link.

## 2026-10-25 — Node.js installed in the home folder
- **Chose (user's choice):** the official Node.js v24.22.1 LTS tarball from nodejs.org, SHA-256 checked against nodejs.org's SHASUMS256.txt, unpacked to `~/.local/node-v24.22.1-darwin-arm64` with a link at `~/.local/node`. No admin rights; delete the folder to uninstall. Use it with `export PATH="$HOME/.local/node/bin:$PATH"`.
- **Alternatives:** the official .pkg installer (system-wide, needs admin); Homebrew (also needs admin, the biggest change).

## 2026-10-25 — Site dependencies, pinned and at least two weeks old
- **Chose:** Vite 8.3.4, TypeScript 6.0.3, Observable Plot 0.6.17, Vitest 5.0.3, each with an exact version in `site/package.json`. Installed with `npm install --before=2026-10-11`, so every indirect dependency was also at least two weeks old when installed. `site/package-lock.json` records every exact version (like `renv.lock`) and is committed. `npm audit`: 0 vulnerabilities. npm's install-script block was left on; the only package affected (`fsevents`) ships ready-built.
- **Why:** brand-new releases are where broken or malicious versions usually show up. Waiting two weeks, plus a lockfile, makes the build reproducible.
- **TypeScript 6, not 7:** 7.0 is the new native (Go) compiler and pulls in about 20 platform-specific binary packages; 6.0.3 is the mature JavaScript compiler. We only use it for type-checking (Vite strips the types itself), so we gain nothing from 7 yet.

## 2026-10-25 — Site data: one small JSON per player
- **Chose:** `pipeline/build_json.py` writes `site/public/data/`:
  - `index.json`: id, name, FGA and tested flag for every player (search);
  - `league.json`: league result per k, each tested player's effect, and the power curve;
  - `players/<id>.json`, one file per player (≈ 1–8 KB): FG%, raw after-makes/misses with Wilson CIs, test results per k, the shuffle distribution as a 40-bin histogram (not 10,000 numbers), and each game's shots as a string like `"1101001"`.

  2.5 MB in total, committed (processed output). A player page downloads about 10 KB.
- **Why:** a static site has no server or database; the browser fetches only what it needs. Like saving `.rds` files for a Shiny app, but readable by any browser.
- **Alternatives:** one big file (about 2.5 MB on every visit); raw CSVs (bigger, untyped, need parsing).

## 2026-10-25 — Site structure and design
- **Routing:** hash routes (`#/` and `#/player/<id>`), so it works on GitHub Pages without server configuration; `base: "./"` makes every path relative.
- **Code:** `src/data.ts` (types mirroring the JSON, cached loading), `src/format.ts` (all numbers and wording, including the "no detectable effect" rule, in one place), `src/search.ts`, `src/charts.ts`, `src/pages/home.ts`, `src/pages/player.ts`.
- **Player page:** verdict badge and a plain-English summary for k = 3; a "how sensitive is this?" sentence from the power curve (the nearest simulated shot count); the corrected effect with CIs for k = 1–3; raw FG% after makes/misses, clearly labelled "not bias-corrected"; the shuffle distributions with the real value; every shot of the season (drawn only when opened); limitations. Players under 300 FGA get the raw numbers, the shots, and a sentence saying why there's no test.
- **Home:** league tiles for k = 1–3, a plain-English result, a "what this does and doesn't show" box, search, and a sorted chart of every tested player (k selectable, hover for details, click to open).
- **Search:** an accessible combobox (arrow keys, Enter, Escape) that ignores accents and punctuation ("doncic" → Dončić, "dangelo" → D'Angelo). Matches are ranked by name start, then tested players, then attempts.
- **Accessibility:**
  - every chart has an aria-label description and a "Show as a table" alternative;
  - verdicts are text plus colour, never colour alone;
  - focus moves to the heading on navigation;
  - skip link;
  - works at 390 px width with no sideways scrolling.
- **Colours:** the same palette as the matplotlib figures, defined once as CSS variables, with separate dark-mode values. Charts read the variables when drawn and redraw on resize or theme change.
- **Tests (`npm test`, Vitest):** normalisation and search; every one of the 582 players is findable by full name and by last name; number formatting; p-values never shown below what the shuffles can resolve; no player summary ever says "no hot hand"; every tested player gets a power sentence.
- **Checked visually** with headless Chrome: desktop, 390 px phone width (in an iframe, because headless Chrome's window can't go below 500 px), dark mode, an untested player, the shot log.
