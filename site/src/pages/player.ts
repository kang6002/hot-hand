// Player page: plain-English verdict, corrected effect, raw FG% after streaks,
// the shuffle test, and every shot of the season.

import { effectsChart, gameLogChart, mountChart, nullChart, rawFgChart, seasonChart } from "../charts";
import { loadIndex, loadLeague, loadPlayer, loadShots, type Player } from "../data";
import {
  esc, int, otherStreaksNote, partialNote, pct, pctInterval, playerSummary, powerSentence, pp, ppInterval, pText, seasonSpan, verdict,
  verdictBadge, verdictLabel, qText,
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
            <td>${qText(t.q_value)}</td><td>${int(t.n_shuffles)}</td><td>${verdictLabel[verdict(t)]}</td></tr>`;
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

function seasonTable(player: Player): string {
  return `
    <table>
      <thead><tr><th>Season</th><th>FGA</th><th>FG%</th>${[1, 2, 3].map((k) => `<th>k = ${k}</th>`).join("")}</tr></thead>
      <tbody>${player.seasons
        .map(
          (s) => `<tr><td>${s.season}</td><td>${int(s.fga)}</td><td>${pct(s.fg_pct)}</td>${
            s.ks
              ? s.ks.map((x) => `<td>${pp(x.effect)} <span class="muted">${ppInterval(x.ci_low, x.ci_high)}</span></td>`).join("")
              : `<td colspan="3" style="text-align:left" class="muted">fewer than ${player.min_fga} attempts</td>`
          }</tr>`,
        )
        .join("")}</tbody>
    </table>`;
}

export async function renderPlayer(app: HTMLElement, id: number, go: (id: number) => void): Promise<void> {
  const [index, league] = await Promise.all([loadIndex(), loadLeague()]);
  let player: Player;
  try {
    player = await loadPlayer(id);
  } catch {
    document.title = "Player not found · Is the Hot Hand Real?";
    app.innerHTML = `<h1 tabindex="-1">Player not found</h1><p>We have no data for this player. <a href="#/">Back to the start page</a>.</p>`;
    app.prepend(searchBox(index.players, go));
    return;
  }
  document.title = `${player.name} · Is the Hot Hand Real?`;
  const headline = player.ks.find((r) => r.k === HEADLINE_K)!;
  const v = verdict(headline.test);
  const power = player.tested ? powerSentence(player, league, HEADLINE_K) : null;
  const partial = partialNote(player);
  const otherNote = player.tested ? otherStreaksNote(player, HEADLINE_K) : null;
  const testedSeasons = player.seasons.filter((s) => s.tested).length;

  app.innerHTML = `
    <div id="search-slot"></div>
    <h1 tabindex="-1">${esc(player.name)}</h1>
    <p class="muted">Regular seasons ${esc(seasonSpan(player).replace(/^(from|in) /, ""))} (${player.n_seasons} season${player.n_seasons > 1 ? "s" : ""}) ·
      ${int(player.fga)} field-goal attempts in ${int(player.games)} games ·
      FG% ${pct(player.fg.pct)} <span class="small">(95% CI ${pctInterval(player.fg.ci_low, player.fg.ci_high)})</span></p>
    ${partial ? `<p class="callout small">${esc(partial)}</p>` : ""}
    ${player.tested ? `<p>${verdictBadge(v)} <span class="muted small">career, after 3 makes in a row</span></p>` : ""}
    <p class="lede">${esc(playerSummary(player, league.n_tested, HEADLINE_K))}</p>
    ${otherNote ? `<p>${esc(otherNote)}</p>` : ""}
    ${power ? `<p class="muted small">${esc(power)}</p>` : ""}

    ${
      player.tested
        ? `
    <h2>Bias-corrected effect (career)</h2>
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

    ${
      testedSeasons
        ? `
    <h2>Season by season</h2>
    <p class="muted small">The effect in each season with at least ${player.min_fga} attempts (${testedSeasons} of ${player.n_seasons}),
      as estimates with 95% confidence intervals only: single seasons have little power, so we don't label them.
      The solid line is the career estimate.</p>
    <div class="segmented" role="group" aria-label="Streak length" id="season-k">
      ${[1, 2, 3].map((k) => `<button type="button" data-k="${k}" aria-pressed="${k === HEADLINE_K}">${k} make${k > 1 ? "s" : ""}</button>`).join("")}
    </div>
    <figure><div class="chart" id="season-chart"></div></figure>
    <details><summary>Show as a table</summary><div class="table-wrap">${seasonTable(player)}</div></details>`
        : ""
    }

    <h2>Raw shooting after streaks (career)</h2>
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
            <figcaption>Real ${pp(r.test!.d_raw)}, shuffle mean ${pp(r.test!.bias)}; ${pText(r.test!.p_value, r.test!.n_shuffles)}, q ${qText(r.test!.q_value).startsWith("<") ? "" : "= "}${qText(r.test!.q_value)}.</figcaption>
          </figure>`,
        )
        .join("")}
    </div>`
        : ""
    }

    <h2>Every shot</h2>
    <details class="game-log">
      <summary>Show every shot, one season at a time: one row per game, shots in order from left to right (solid: make, faint: miss)</summary>
      <p><label>Season <select id="log-season">${[...player.seasons].reverse().map((s) => `<option>${s.season}</option>`).join("")}</select></label></p>
      <div class="chart" id="game-log-chart"></div>
    </details>

    <div class="callout">
      <strong>Limits of this analysis.</strong>
      <ul>
        <li>Shot difficulty isn't controlled: after makes, players may take harder shots, and defences may adjust.</li>
        <li>Putbacks and tip-ins mostly follow misses and go in often, which lowers the effect a little (league-wide, removing them changes it by less than half a percentage point).</li>
        <li>Missed shots on shooting fouls aren't recorded as field-goal attempts.</li>
        <li>Limited power: small effects are hard to detect for a single player, even over a career, so "no detectable effect" is not proof that there is no hot hand.</li>
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
  if (testedSeasons) {
    const showSeason = (k: number) => mountChart(app.querySelector("#season-chart")!, seasonChart(player, k));
    app.querySelectorAll<HTMLButtonElement>("#season-k button").forEach((btn) =>
      btn.addEventListener("click", () => {
        app.querySelectorAll("#season-k button").forEach((x) => x.setAttribute("aria-pressed", String(x === btn)));
        showSeason(Number(btn.dataset.k));
      }),
    );
    showSeason(HEADLINE_K);
  }

  // Load and draw the shot log only when it is opened (it can be large)
  const log = app.querySelector<HTMLDetailsElement>(".game-log")!;
  const select = log.querySelector<HTMLSelectElement>("#log-season")!;
  const drawLog = async () => {
    const seasons = await loadShots(player.id);
    const season = seasons.find((x) => x.season === select.value) ?? seasons.at(-1)!;
    mountChart(log.querySelector<HTMLElement>("#game-log-chart")!, gameLogChart(player.name, season));
  };
  log.addEventListener("toggle", () => {
    if (log.open && !log.querySelector("#game-log-chart")!.hasChildNodes()) drawLog();
  });
  select.addEventListener("change", drawLog);
}
