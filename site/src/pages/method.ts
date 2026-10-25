// Method page: how the test works, in plain language, with the numbers behind each choice.

import { loadLeague, type League } from "../data";
import { int } from "../format";

function powerTable(league: League): string {
  const fgas = [...new Set(league.power.map((r) => r.fga))].sort((a, b) => a - b);
  const boosts = [...new Set(league.power.map((r) => r.boost))].filter((b) => b > 0).sort((a, b) => a - b);
  const cell = (k: number, fga: number, boost: number) => {
    const r = league.power.find((x) => x.k === k && x.fga === fga && Math.abs(x.boost - boost) < 1e-9);
    return r ? `${Math.round(100 * r.power_05)}%` : "–";
  };
  return `
    <table>
      <thead>
        <tr><th>Shots</th>${[1, 3].flatMap((k) => boosts.map((b) => `<th>k = ${k}, +${Math.round(100 * b)} pp</th>`)).join("")}</tr>
      </thead>
      <tbody>${fgas
        .map((f) => `<tr><td>${int(f)}</td>${[1, 3].flatMap((k) => boosts.map((b) => `<td>${cell(k, f, b)}</td>`)).join("")}</tr>`)
        .join("")}</tbody>
    </table>`;
}

export async function renderMethod(app: HTMLElement): Promise<void> {
  const league = await loadLeague();
  document.title = "Method · Is the Hot Hand Real?";
  app.innerHTML = `
    <h1 tabindex="-1">How the test works</h1>
    <p class="lede">The question: after a player makes a few shots in a row, is their next shot more likely to go in
      than after the same number of misses? Answering it honestly takes more care than it seems.</p>

    <h2>1. The obvious comparison is misleading</h2>
    <p>The natural approach is to compare a player's field-goal percentage right after k makes in a row with their
      percentage right after k misses in a row (we use k = 1, 2 and 3; k = 3 is the headline, as in the classic
      studies). This raw difference is biased, even for a player whose shots are pure coin flips:</p>
    <ul>
      <li><strong>It is biased downward within a sequence of shots.</strong> In a finite sequence, the shots that
        follow a streak of makes come from a pool that has already "used up" some makes. For a 50% shooter taking 100 shots,
        the raw difference after 3 makes averages about −8 percentage points with no hot hand at all. Miller and Sanjurjo
        (2018) showed this bias in the famous 1985 study by Gilovich, Vallone and Tversky, which had concluded that the hot
        hand is a "fallacy".</li>
      <li><strong>It is biased upward when games are pooled.</strong> On a good night a player makes more shots,
        so more of their shots follow makes, and those shots also go in more often. Pooling good and bad nights makes the
        raw difference look like a hot hand. In our simulations of players without a hot hand but with good and bad
        nights, the raw difference after 3 makes averaged about +6 points.</li>
    </ul>
    <p>Which bias wins depends on the player, so no fixed formula can correct it. For real players we found
      corrections ranging from about −20 to +20 points within a single season.</p>

    <h2>2. The shuffle test</h2>
    <p>For each player we shuffle the order of their makes and misses <em>within each game</em>, thousands of times
      (10,000 at first, up to 1,000,000 when the result is extreme). Shuffling keeps how many shots went in each game, so
      good and bad nights stay exactly as they were, but it destroys any real streakiness. Computing the raw difference
      in every shuffled version shows what luck alone produces <em>for this player's games</em>, including both biases.</p>
    <ul>
      <li><strong>Effect</strong> = the real raw difference − the average shuffled difference, in percentage points.</li>
      <li><strong>p-value</strong> = the share of shuffles at least as far from their average as the real value (two-sided:
        a "cold hand" counts too).</li>
      <li><strong>95% confidence interval</strong>: we resample whole games with replacement 2,000 times, re-estimating
        the bias in every resample. In simulations these intervals contain the true value about 94–95% of the time.</li>
    </ul>
    <p>We checked the test on simulated players with no hot hand: it flags about 5% of them at the 5% level, as it should.</p>

    <h2>3. Testing hundreds of players</h2>
    <p>With ${int(league.n_tested)} players tested, some will look streaky by chance. We use the Benjamini–Hochberg procedure to keep the
      expected share of false discoveries among flagged players at ${Math.round(100 * league.fdr_q)}% (separately for each k).
      A player is only labelled "detectable hot hand" or "detectable cold hand" if they survive this correction.
      Everyone else gets "no detectable effect".</p>

    <h2>4. Careers, seasons and the league</h2>
    <ul>
      <li>The main test pools a player's whole career (all regular-season games since 1996-97, still shuffling within games).
        More shots give more power, and testing each season separately would multiply the number of tests.</li>
      <li>Per-season results are shown as estimates with confidence intervals only, without significance labels.</li>
      <li>Players need at least ${league.min_fga} attempts to be tested; below that, the test can't say anything useful.</li>
      <li>The league-wide estimate is the average of the tested players' effects, weighted by their number of shots. Its
        p-value combines the players' shuffles, and its interval combines their resamples.</li>
    </ul>

    <h2>5. What the test can and can't detect</h2>
    <p>How often a hot hand of a given size is detected (at the 5% level), from 200 simulated players per cell. A
      "+5 pp" hot hand means the chance of a make rises by 5 percentage points after k makes in a row.</p>
    <div class="table-wrap">${powerTable(league)}</div>
    <p>Published estimates of real hot-hand effects are mostly a few percentage points. With one season of shots, only
      very large effects are reliably detected, and careers help a lot. This is why we say "no detectable effect",
      never "no hot hand".</p>

    <h2>6. Data checks</h2>
    <ul>
      <li><strong>Shot order.</strong> The NBA's event numbers turned out to be the order events were <em>typed in</em>,
        so shots logged late would land in the wrong place. We order shots by the game clock instead; this matched the
        NBA's own play-by-play sequence in all 967 player-games we checked, across six eras from 1996-97 to 2025-26.</li>
      <li>Streaks never cross games. Raw downloads are checked for missing games, duplicates and truncated responses.</li>
    </ul>

    <h2>7. Limitations</h2>
    <ul>
      <li><strong>Shot difficulty.</strong> After making shots, players may take harder shots and defences may adjust.
        We don't control for this yet, and it is the most likely reason the league-wide effect is slightly negative.</li>
      <li><strong>Putbacks and tip-ins</strong> mostly follow misses and go in often. Removing them changes the 2025-26
        league-wide effect only a little (after 3 makes: −2.0 → −1.6 percentage points).</li>
      <li>Missed shots on shooting fouls are not recorded as field-goal attempts.</li>
      <li>Shot-level data starts in 1996-97, so earlier parts of careers are missing.</li>
    </ul>

    <h2>References</h2>
    <ul class="small">
      <li>Gilovich, T., Vallone, R. & Tversky, A. (1985). The hot hand in basketball: On the misperception of random
        sequences. <em>Cognitive Psychology</em>, 17(3), 295–314.</li>
      <li>Miller, J. B. & Sanjurjo, A. (2018). Surprised by the hot hand fallacy? A truth in the law of small numbers.
        <em>Econometrica</em>, 86(6), 2019–2047.</li>
      <li>Bocskocsky, A., Ezekowitz, J. & Stein, C. (2014). The hot hand: A new approach to an old "fallacy".
        MIT Sloan Sports Analytics Conference.</li>
      <li>Benjamini, Y. & Hochberg, Y. (1995). Controlling the false discovery rate: A practical and powerful approach
        to multiple testing. <em>Journal of the Royal Statistical Society B</em>, 57(1), 289–300.</li>
    </ul>`;
}
