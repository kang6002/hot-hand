// Player page: plain-English verdict, corrected effect, raw FG% after streaks,
// the shuffle test, and every shot of the season.

import { effectsChart, gameLogChart, mountChart, nullChart, rawFgChart } from "../charts";
import { loadIndex, loadLeague, loadPlayer, type Player } from "../data";
import {
  esc, int, pct, pctInterval, playerSummary, powerSentence, pp, ppInterval, pText, verdict, verdictBadge, verdictLabel,
} from "../format";
import { searchBox } from "../search";

const HEADLINE_K = 3;

function testTable(player: Player): string {
  return `
    <table>
      <thead><tr><th>Streak</th><th>Raw difference</th><th>Bias</th><th>Effect</th><th>95% CI</th><th>p</th><th>q</th><th>Shuffles</th><th>Result</th></tr></thead>
      <tbody>${player.ks
        .map((r) => {
          const t = r.test!;
          return `<tr><td>k = ${r.k}</td><td>${pp(t.d_raw)}</td><td>${pp(t.bias)}</td><td>${pp(t.effect)}</td>
            <td>${ppInterval(t.ci_low, t.ci_high)}</td><td>${pText(t.p_value, t.n_shuffles).replace("p ", "").replace("= ", "")}</td>
            <td>${t.q_value.toFixed(2)}</td><td>${int(t.n_shuffles)}</td><td>${verdictLabel[verdict(t)]}</td></tr>`;
        })
        .join("")}</tbody>
    </table>`;
}

function rawTable(player: Player): string {
  return `
    <table>
      <thead><tr><th>Streak</th><th>After makes</th><th>Shots</th><th>After misses</th><th>Shots</th></tr></thead>
      <tbody>${player.ks
        .map(
          (r) => `<tr><td>k = ${r.k}</td>
            <td>${pct(r.after_makes.pct)} <span class="muted">(${pctInterval(r.after_makes.ci_low, r.after_makes.ci_high)})</span></td><td>${int(r.after_makes.n)}</td>
            <td>${pct(r.after_misses.pct)} <span class="muted">(${pctInterval(r.after_misses.ci_low, r.after_misses.ci_high)})</span></td><td>${int(r.after_misses.n)}</td></tr>`,
        )
        .join("")}
        <tr><td>Overall</td><td colspan="4" style="text-align:left">${pct(player.fg.pct)} <span class="muted">(${pctInterval(player.fg.ci_low, player.fg.ci_high)})</span>, ${int(player.fga)} shots</td></tr>
      </tbody>
    </table>`;
}

export async function renderPlayer(app: HTMLElement, id: number, go: (id: number) => void): Promise<void> {
  const [index, league] = await Promise.all([loadIndex(), loadLeague()]);
  let player: Player;
  try {
    player = await loadPlayer(id);
  } catch {
    document.title = "Player not found · Is the Hot Hand Real?";
    app.innerHTML = `<h1 tabindex="-1">Player not found</h1><p>We have no ${esc(index.season)} data for this player. <a href="#/">Back to the start page</a>.</p>`;
    app.prepend(searchBox(index.players, go));
    return;
  }
  document.title = `${player.name} · Is the Hot Hand Real?`;
  const headline = player.ks.find((r) => r.k === HEADLINE_K)!;
  const v = verdict(headline.test);
  const power = player.tested ? powerSentence(player, league, HEADLINE_K) : null;

  app.innerHTML = `
    <div id="search-slot"></div>
    <h1 tabindex="-1">${esc(player.name)}</h1>
    <p class="muted">${esc(player.season)} regular season · ${int(player.fga)} field-goal attempts in ${player.games} games ·
      FG% ${pct(player.fg.pct)} <span class="small">(95% CI ${pctInterval(player.fg.ci_low, player.fg.ci_high)})</span></p>
    ${player.tested ? `<p>${verdictBadge(v)} <span class="muted small">after 3 makes in a row</span></p>` : ""}
    <p class="lede">${esc(playerSummary(player, league.n_tested, HEADLINE_K))}</p>
    ${power ? `<p class="muted small">${esc(power)}</p>` : ""}

    ${
      player.tested
        ? `
    <h2>Bias-corrected effect</h2>
    <p class="muted small">FG% after k makes in a row minus FG% after k misses in a row, minus the difference that shuffling this player's shots within each game produces (the bias). 0 means no difference beyond luck.</p>
    <figure>
      <div class="legend">
        <span><span class="key" style="background: var(--neutral)"></span>no detectable effect</span>
        <span><span class="key" style="background: var(--hot)"></span>detectable hot hand</span>
        <span><span class="key" style="background: var(--cold)"></span>detectable cold hand</span>
      </div>
      <div class="chart" id="effects-chart"></div>
      <figcaption>Dots: effect; lines: 95% confidence interval (resampling games).</figcaption>
    </figure>
    <details><summary>Show as a table</summary><div class="table-wrap">${testTable(player)}</div></details>`
        : ""
    }

    <h2>Raw shooting after streaks</h2>
    <p class="muted small"><strong>Not bias-corrected.</strong> These raw percentages are what most people compare, but the
      difference between them is biased (in either direction) even for a player with no hot hand. They are shown for context only.</p>
    <figure>
      <div class="legend">
        <span><span class="key" style="background: var(--after-makes)"></span>after k makes in a row</span>
        <span><span class="key" style="background: var(--after-misses)"></span>after k misses in a row</span>
        <span><span class="key dash"></span>overall FG%</span>
      </div>
      <div class="chart" id="raw-chart"></div>
      <figcaption>Dots: FG% on the next shot in the same game; lines: 95% Wilson confidence interval.</figcaption>
    </figure>
    <details><summary>Show as a table</summary><div class="table-wrap">${rawTable(player)}</div></details>

    ${
      player.tested
        ? `
    <h2>The shuffle test</h2>
    <p class="muted small">We shuffle the order of ${esc(player.name.split(" ")[0])}'s makes and misses within each game thousands of times.
      Shuffling keeps how many shots went in each game but destroys any real streakiness, so the grey distribution shows
      what luck alone produces, including the bias. The effect is how far the real value (solid line) sits from the
      middle of the shuffles (dashed line).</p>
    <div class="legend">
      <span><span class="key line"></span>real games</span>
      <span><span class="key dash"></span>shuffle mean (bias)</span>
      <span><span class="key" style="background: var(--null-fill); border-radius: 2px"></span>shuffled games</span>
    </div>
    <div class="small-multiples">
      ${player.ks
        .map(
          (r) => `<figure>
            <h3>After ${r.k === 1 ? "a make" : `${r.k} makes`}: ${pp(r.test!.effect)}</h3>
            <div class="chart" id="null-chart-${r.k}"></div>
            <figcaption>Real ${pp(r.test!.d_raw)}, shuffle mean ${pp(r.test!.bias)}; ${pText(r.test!.p_value, r.test!.n_shuffles)}, q = ${r.test!.q_value.toFixed(2)}.</figcaption>
          </figure>`,
        )
        .join("")}
    </div>`
        : ""
    }

    <h2>Every shot</h2>
    <details class="game-log">
      <summary>Show all ${int(player.fga)} shots: one row per game, shots in order from left to right (solid: make, faint: miss)</summary>
      <div class="chart" id="game-log-chart"></div>
    </details>

    <div class="callout">
      <strong>Limits of this analysis.</strong>
      <ul>
        <li>Shot difficulty isn't controlled: after makes, players may take harder shots, and defences may adjust.</li>
        <li>Putbacks and tip-ins mostly follow misses and go in often, which lowers the effect.</li>
        <li>Missed shots on shooting fouls aren't recorded as field-goal attempts.</li>
        <li>One season gives limited power: "no detectable effect" is not proof that there is no hot hand.</li>
      </ul>
    </div>
    <p><a href="#/">← All players</a></p>`;

  app.querySelector("#search-slot")!.replaceWith(searchBox(index.players, go));
  if (player.tested) {
    mountChart(app.querySelector("#effects-chart")!, effectsChart(player));
    for (const r of player.ks) {
      if (r.test?.null_hist) mountChart(app.querySelector(`#null-chart-${r.k}`)!, nullChart(r.test.null_hist, r.test.d_raw, r.test.bias, r.k));
    }
  }
  mountChart(app.querySelector("#raw-chart")!, rawFgChart(player));
  // Draw the (large) game log only when it is opened
  const log = app.querySelector<HTMLDetailsElement>(".game-log")!;
  log.addEventListener("toggle", () => {
    const el = log.querySelector<HTMLElement>("#game-log-chart")!;
    if (log.open && !el.hasChildNodes()) mountChart(el, gameLogChart(player));
  });
}
