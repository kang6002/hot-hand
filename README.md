# Is the Hot Hand Real?

**Live site: https://kang6002.github.io/hot-hand/**

Does an NBA player's next shot go in more often after a streak of makes? This project tests that question for
every player, using every regular-season field-goal attempt since 1996-97 (when shot-level data begins):
5.8 million shots and about 2,800 players. Every player has a searchable page with an effect size, a confidence
interval and a plain-English verdict.

## Results

Regular-season careers, 1996-97 to 2025-26; 1,676 players with at least 300 attempts tested.

| Streak | League-wide effect (bias-corrected) | 95% CI | Players with a detectable hot hand | … cold hand |
|---|---|---|---|---|
| After 1 make | −1.05 pp | [−1.14, −0.98] | 0 | 19 |
| After 2 makes in a row | −1.22 pp | [−1.33, −1.11] | 0 | 7 |
| After 3 makes in a row | −1.16 pp | [−1.33, −0.99] | 0 | 0 |

- **No player shows a detectable hot hand** after correcting for testing 1,676 players (Benjamini–Hochberg, q = 0.05).
  That is not proof that hot hands don't exist: simulations show that effects of a few percentage points are hard to
  detect for a single player, even over a career.
- **League-wide, shots right after makes go in about 1 percentage point *less* often** than after the same number of
  misses, a small but very precise effect.
- The players flagged for shooting worse after makes are mostly high-volume shot creators (for example Luka Dončić,
  Giannis Antetokounmpo, LeBron James, James Harden). The most likely explanation is **shot selection**: after
  makes, players take harder shots and defences tighten. Shot difficulty isn't controlled yet; that's the next step.

## Why the obvious comparison is wrong

Comparing a player's FG% right after k makes in a row with their FG% right after k misses in a row is biased,
even for a player with no hot hand, and in both directions:

- **Downward within a sequence of shots.** In a finite sequence, shots that follow a streak of makes come from a pool
  that has "used up" some makes (Miller & Sanjurjo, 2018). For a 50% shooter taking 100 shots, the raw difference after
  3 makes averages about −8.6 percentage points with no hot hand at all.
- **Upward when games are pooled.** On good nights more shots follow makes *and* more shots go in. In our
  simulations of players without a hot hand but with good and bad nights, the raw difference averaged +6.1 points.

## Method (short version; details on the site's Method page and in [DECISIONS.md](DECISIONS.md))

- **Shuffle test.** For each player, shuffle the order of makes and misses *within each game* 10,000 times (up to
  1,000,000 for extreme results). This keeps each game's make count but removes any real streakiness, so the average
  shuffled difference is the bias. **Effect = real difference − average shuffled difference.** Two-sided p-value from
  the shuffles; 95% confidence interval from resampling games (re-estimating the bias in every resample).
- **Validated on simulated players:** the test flags about 5% of players with no hot hand at the 5% level, the
  intervals cover the truth about 94–95% of the time, and a power curve shows which effect sizes it can detect.
- **Many players:** Benjamini–Hochberg false-discovery-rate control (q = 0.05) across all tested players, per k.
- **Careers are the main test** (≥ 300 career attempts). Per-season results are shown as estimates with CIs only.
- **Wording:** "no detectable effect", never "no hot hand". Small real effects are hard to detect for a single player.

## Data checks we had to make

- The stats API silently returns at most 102,400 rows per request, so each season is downloaded month by month,
  and any response of exactly that size is treated as truncated.
- The NBA's event numbers are the order events were *typed in*, so shots logged late are out of order. Shots are
  ordered by the game clock instead; this matched the NBA's play-by-play sequence in 967 of 967 sampled player-games
  across six eras.
- Every season was checked for missing games and duplicates; every gap is a known cancellation (lockouts, the 2013
  Boston Marathon bombing, COVID).

## Limitations

- **Shot difficulty isn't controlled yet.** After makes, players may take harder shots and defences may adjust.
- Putbacks and tip-ins mostly follow misses and go in often; removing them changes the 2025-26 league-wide effect only
  a little (after 3 makes: −2.0 → −1.6 percentage points).
- Missed shots on shooting fouls are not recorded as field-goal attempts.
- Careers that began before 1996-97 are partial (flagged on the player page).

## Reproduce it

Requirements: Python 3.13 and Node.js 24. Downloads must run on your own computer (stats.nba.com blocks most cloud
servers) and take about 30 minutes; the full career analysis takes one to two hours on an 8-core laptop.

```bash
# Python environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Pipeline (run from the project root)
.venv/bin/python pipeline/download.py all           # raw shots, cached in data/raw/ (not committed)
.venv/bin/python pipeline/clean.py all              # ordered, checked shots
.venv/bin/python pipeline/player_info.py            # first season of every player
.venv/bin/python pipeline/analyse.py career         # main test, BH-FDR, league estimate
.venv/bin/python pipeline/analyse.py seasons all    # per-season estimates
.venv/bin/python pipeline/power.py                  # power curve (simulations)
.venv/bin/python pipeline/build_json.py             # data files for the website

# Tests
.venv/bin/python -m pytest            # fast tests
.venv/bin/python -m pytest -m slow    # calibration simulations (~2 min)

# Website
cd site
npm ci
npm test
npm run dev                            # local preview
```

## Project layout

```
pipeline/   Python: download, clean, statistics (stats.py), analysis, simulations, JSON for the site
tests/      pytest: hand-built sequences, simulated shooters, calibration checks
site/       Vite + TypeScript + Observable Plot website (data in site/public/data/)
data/       processed results (CSV); raw downloads stay local
figures/    matplotlib figures from Milestone 1
PLAN.md     agreed scope and statistical plan; DECISIONS.md: every decision with reasons and alternatives
```

## Data and attribution

Data: NBA.com Stats via [nba_api](https://github.com/swar/nba_api). Not affiliated with or endorsed by the NBA.
The data belongs to the NBA and is used for personal, non-commercial purposes under the NBA.com terms of use. This
repository publishes only derived statistics, not raw data.

## Licence

The code is released under the [MIT licence](LICENSE). The NBA data and anything derived from it are not covered by
this licence; they remain subject to the NBA.com terms of use.

## References

- Gilovich, Vallone & Tversky (1985). The hot hand in basketball. *Cognitive Psychology* 17(3), 295–314.
- Miller & Sanjurjo (2018). Surprised by the hot hand fallacy? *Econometrica* 86(6), 2019–2047.
- Bocskocsky, Ezekowitz & Stein (2014). The hot hand: A new approach to an old "fallacy". MIT Sloan Sports Analytics Conference.
- Benjamini & Hochberg (1995). Controlling the false discovery rate. *JRSS B* 57(1), 289–300.

Built with [Claude Code](https://claude.com/claude-code) as a coding assistant.
