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

## 2026-10-25 — Putback/tip-in sensitivity check (moved forward from Milestone 4 at the user's request)
- **Question:** putbacks and tip-ins mostly follow misses and go in often. Do they explain the negative league-wide effect?
- **Method** (`pipeline/sensitivity_putbacks.py`):
  - Remove the four putback/tip-in shot types (Tip Layup, Putback Layup, Tip Dunk, Putback Dunk) from every shot sequence: 9,915 shots, 4.5% of all shots, FG% 59.7%. They follow the player's own miss 50–58% of the time, against 46% for all shots.
  - Rerun the whole analysis (shuffles, bootstrap, BH, league estimate) on the **same 284 players** as the main run, for a like-for-like comparison; 12 of them now have fewer than 300 FGA.
  - To reuse the code, `analyse.py` was split into `analyse_season()` plus `main()`. Rerunning the main analysis afterwards reproduced the committed CSVs byte for byte.
- **Result** (league-wide effect, main → without putbacks):
  - k = 1: −1.03 → −0.95 pp;
  - k = 2: −1.32 → −1.21 pp;
  - k = 3: −2.03 → −1.58 pp (95% CI [−2.47, −0.59], p = 0.002).

  Putbacks explain 8%, 9% and 22% of the effect. The effect stays negative and clearly non-zero for every k, and there are still 0 BH discoveries. Player-level effects barely move for k = 1–2 (correlation 0.94 and 0.91 with the main run); for k = 3 the correlation is 0.62, because removing shots changes many short streaks.
- **Meaning:** putbacks are a minor part of the negative effect. The most likely remaining explanation is shot selection and defence after makes (harder shots), which needs the shot-difficulty control (Milestone 4).
- **Site:** `league.json` now carries the no-putback league result. The home page states it ("without them, the effect after 3 makes in a row is −1.6 pp … instead of −2.0 pp"), and the player-page limitation says putbacks change the league effect by less than half a percentage point.
- **Alternatives:** keep putbacks in the history but not as predicted shots (breaks the shuffle logic, because putback outcomes would be shuffled into other positions); model shot type in a regression (that's the shot-difficulty work in Milestone 4).

## 2026-10-25 — Milestone 3: all seasons downloaded and cleaned
- **Download:** `pipeline/download.py all`: 29 new seasons × 11 monthly requests (319 requests, ≈ 5 s each including the 3 s pause), no failed requests, no truncated responses. 5.8 million shots, 1.4 GB raw (git-ignored).
- **Completeness:** no duplicate shots in any season. Game counts: 1,189 per season until 2003-04 (29 teams), 1,230 from 2004-05. The gaps all have known explanations (from memory, still to be checked against the official schedule):
  - 1998-99 (725 games) and 2011-12 (990): lockouts;
  - 2012-13: game 1214 missing, the Celtics–Pacers game cancelled after the Boston Marathon bombing;
  - 2019-20: games 972–1230 never played (season suspended for COVID); 88 "bubble" seeding games numbered 1231–1318; game 707 is very likely the Lakers–Clippers game postponed after Kobe Bryant's death and never made up;
  - 2020-21 (1,080): 72-game season.
- **Cleaning** (`pipeline/clean.py all`, 37 s): every season passed all checks (only attempts; make flag matches the event type; no duplicates; no player on two teams in a game). Per-season numbers are in `data/processed/data_quality.csv` (committed). Late-logged shots (event numbers out of clock order): 0.05–0.15% of shots before 2017-18, ≈ 0.3% since. Clock ordering handles both.
- **Shot order checked across eras** (`pipeline/check_order.py`, 8 games each from 1996-97, 2001-02, 2006-07, 2011-12, 2016-17, 2021-22, plus 10 from 2025-26): clock order matched the NBA's play-by-play sequence in 967/967 player-games (event-number order: 907/967). **Caveat found:** for events in the same second, the NBA's own sequence also just follows logging order (e.g. a 1996 game shows a made shot before the miss and rebound that preceded it). So this check confirms agreement with the NBA's sequence; it doesn't independently prove the on-court order of same-second events. Those are rare (≈ 0.15% of shots) and mostly a miss followed by a tip-in.

## 2026-10-25 — Milestone 3: careers, seasons, partial careers
- **Career test (main result):** all of a player's regular-season games 1996-97 → 2025-26 pooled, still shuffling within games; tested with ≥ 300 career FGA (1,676 of 2,839 players). Extra shuffles up to 1,000,000 for extreme results, then BH-FDR per k across the 1,676 players, and an all-time league estimate.
- **Per-season estimates:** every player-season with ≥ 300 FGA that season gets an effect and a 95% CI, but no p-value or label on the site (PLAN.md: per-season results are descriptive). 2,000 shuffles per player-season are enough, since only the bias (the shuffle mean) and the CI are needed: the shuffle mean's standard error is about sd/45, under 0.2 pp for k = 3. League estimate per season from the same runs.
- **Partial careers:** `pipeline/player_info.py` makes one request to CommonAllPlayers (first and last season for 5,198 players). Careers with a first season before 1996-97 get a note on the player page (e.g. Michael Jordan, Kevin Garnett; not Kobe Bryant, whose first season was 1996-97). Every player in the shot data is in that list. Names on the site also come from it, because the shot data can carry old names.
- **Parallel processing:** `analyse.py` runs players on all CPU cores (largest careers first) with seeds that depend only on the player (and season), so results don't depend on processing order. The parallel version reproduced the Milestone 1 results byte for byte.
- **Lesson (CPU oversubscription):** the first career run had a load average of 38–45 on 8 cores. Each worker process also let Apple Accelerate (numpy's maths library) start ≈ 13 threads for the bootstrap's matrix product. Fix: one maths thread per worker (`VECLIB_MAXIMUM_THREADS=1` and equivalents, set before numpy is imported). Stopping that run also left its 8 worker processes orphaned and still computing; they had to be stopped separately. To stop a parallel run, stop its workers too.
- **Power curve** extended to 12,000 and 24,000 FGA (careers), reusing the existing scenarios (seeded, so only new ones run). With 24,000 shots, a +5 pp hot hand after 3 makes is detected 84% of the time at α = 0.05 (one season of 1,500 shots: 11%). A +2 pp effect is still hard to detect (28%). One no-hot-hand cell (k = 3, 24,000 shots) gave 8.5% false positives from 200 simulations, within chance across the 24 such cells; the 4,000-player calibration was on target.

## 2026-10-25 — Milestone 3: site structure and deployment
- **Pages:**
  - Home: the all-time result in brief, plus search;
  - League (new): all-time tiles, the league effect season by season, every tested player's career effect;
  - Player: career verdict and summary, a partial-career note, the corrected career effect, a new season-by-season chart and table (estimates only, no labels), raw FG%, the shuffle test, and the shot log one season at a time;
  - Method and About (new).

  Navigation marks the current page (`aria-current`).
- **Data files:** shot logs moved to `shots/<id>.json`, loaded only when the shot log is opened (LeBron alone has ≈ 29,000 shots). Every tested player's career effect moved to `league_players.json`, loaded only by the League page, which keeps the home page light. The putback check is stored with its own season's main result, so the site always compares 2025-26 with 2025-26, never with the all-time numbers.
- **Deployment:** `.github/workflows/deploy.yml` runs on every push to main: `npm ci`, the site tests, build, publish to GitHub Pages. Each Action is pinned to an exact commit of a release at least two weeks old (checkout v7.0.1, setup-node v7.1.0, configure-pages v6.0.0, upload-pages-artifact v5.0.0, deploy-pages v5.0.1). Least-privilege permissions per job: build has read-only access; only deploy can write to Pages. The workflow never contacts NBA.com: data comes from the committed JSON.

## 2026-10-25 — Publishing: GitHub identity, licence, terms
- **Commit identity (user chose option A):** name "Kang Rui Li" with GitHub's private address `185619610+kang6002@users.noreply.github.com`, so commits link to the GitHub profile without exposing a real email. Git had never been configured, so the first three commits carried an automatic `…@Kangs-MacBook-Air.local` address. They were rebuilt with the new identity before anything was published (same files and dates, verified tree by tree). A first attempt went wrong: zsh passed `-p <parent>` as one argument, collapsing the history to one commit. The original commits were still in git's object store, so the history was rebuilt from them, and `main` was only moved after all three rebuilt commits had matching content.
- **GitHub CLI:** `gh` v2.102.0 (release at least two weeks old), official zip with its SHA-256 verified, installed to `~/.local/gh` (no admin). Logged in by the user (`gh auth login`, stored in the macOS keychain). The first login couldn't be saved because `~/.config` was owned by root (left over from an earlier administrator install); the user fixed it with `sudo chown -R kangruili ~/.config`.
- **Licence (user chose MIT):** for the code only; the README states that the NBA data and derived statistics stay under the NBA.com terms.
- **Terms:** the user read the NBA.com terms of use and is comfortable publishing derived statistics with attribution, non-commercially.

## 2026-10-25 — Milestone 3 results and the long career run
- **Career results** (1,676 players, ≥ 300 career FGA, 1996-97 → 2025-26):
  - league-wide effect −1.05 pp [−1.14, −0.98] (k = 1), −1.22 [−1.33, −1.11] (k = 2), −1.16 [−1.33, −0.99] (k = 3), all p < 0.0002;
  - BH discoveries: 0 hot for every k; cold: 19 (k = 1), 7 (k = 2), 0 (k = 3);
  - 58–68% of players have negative effects, and 7–12% have p < 0.05 (more than the 5% expected from luck alone).

  The flagged players are mostly high-volume shot creators (e.g. Dončić, Antetokounmpo, LeBron James, Harden, Maxey, Edwards), which fits a shot-selection ("heat check") explanation that we can't test without shot-difficulty control.
- **Per-season league estimates:** negative in all 30 seasons at k = 3 (−0.2 to −2.5 pp); the CI excludes 0 in 18 of 30; no clear trend. The 2025-26 per-season estimate (−2.03 pp, 2,000 shuffles) matches the Milestone 1 run (10,000+ shuffles): a consistency check.
- **Wording for flagged players:** "detectable cold hand" always comes with the shot-selection caveat ("this doesn't show that the player's skill drops"). Players flagged only for shorter streaks get a "Shorter streaks tell a different story" sentence, so the page never shows a flagged chart under an unflagged summary without explanation.
- **Runtime (2 h 24 min) and what we changed during it:**
  1. `pool.map(chunksize=4)` with biggest-first ordering gave one worker the four longest careers to run back to back (an estimated 2–3 hours on one core). Now each worker takes one player at a time.
  2. Progress was reported in submission order, so one slow player hid everything behind it. Now results are collected as they finish.
  3. **New stopping rule for extra shuffles:** a k is settled when ≥ 100 shuffles are as extreme as the data, *or* when p ≤ q / (number of tests). BH always flags such a p-value, whatever the other p-values are, so more shuffles can't change the result. This kept LeBron (b = 0 at 10,000 shuffles) at 100,000 instead of 1,000,000.
  4. Even so, 116 players needed extra shuffles (26 of them 1,000,000, about an hour of one core each for long careers). That is far more than in one season, because careers give the test much more power.
- **Statistical note for next time:** a Monte Carlo p-value (b+1)/(B+1) is valid for any B, and BH with valid p-values still controls the false discovery rate. So capping extra shuffles at 100,000 would be statistically fine and only slightly less precise near the cut-off. Next time: cap at 100,000, save each player's result as it finishes (so a stop loses nothing), and split a single long career's shuffles across cores.
- **Site checks:** 10 site tests pass. A search test failed at first because 54 players share the last name Williams, more than the test's limit; the test now allows all matches. A timeout followed (5,700 searches re-normalising every name); names are now normalised once per player, which also speeds up the real search box. Display fixes after visual checks: duplicate axis ticks, "q = 0.00" (now "< 0.001" or three decimals), clipped season labels (now "03-04").

## 2026-10-25 — Published
- **Pre-publish checks:** 5,717 files staged; no raw or interim data, node_modules or build output; the largest file is 8 MB (GitHub's limit is 100 MB); no tokens, keys or the user's real email anywhere (DECISIONS.md was checked separately, because it legitimately mentions the GitHub noreply address).
- **Order of operations:** create the public repository → enable GitHub Pages in workflow mode (`POST /repos/kang6002/hot-hand/pages`, `build_type=workflow`) → push. That way the first workflow run could deploy straight away.
- **Verified live:** the workflow (npm ci, tests, build, deploy) succeeded in about 45 s; the page and data files return HTTP 200; player and League pages render on the live site; phone-width layout checked.
- **Fix after publishing:** the 30 season labels overlapped at phone width, so the charts now show every n-th label when there isn't room for all. Pushed and redeployed automatically.
- **Testing note:** headless Chrome screenshots of the *live* site inside an iframe from a local file stayed blank, and so did the League page when two frames shared one time budget. Loading the same pages directly (`--dump-dom`) showed they render correctly with no JavaScript errors, so this was an artefact of the test setup, not a site bug.
