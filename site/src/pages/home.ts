// Home: league-wide result, search, and every tested player's effect.

import { leagueChart, mountChart } from "../charts";
import { loadIndex, loadLeague, type League } from "../data";
import { esc, int, pp, ppInterval, pText } from "../format";
import { searchBox } from "../search";

const streakName = (k: number) => (k === 1 ? "After a make" : `After ${k} makes in a row`);

function leagueSentence(league: League, k: number): string {
  const r = league.ks.find((x) => x.k === k)!;
  const n = r.discoveries_hot + r.discoveries_cold;
  const players = `${int(r.n_players)} players with at least ${league.min_fga} attempts`;
  const excludesZero = r.ci_low > 0 || r.ci_high < 0;
  const overall = excludesZero
    ? `Across the ${players}, a shot taken right after ${k === 1 ? "a make" : `${k} makes in a row`} went in ${(100 * Math.abs(r.effect)).toFixed(1)} percentage points ${r.effect > 0 ? "more" : "less"} often than after the same number of misses, once the statistical bias is removed (95% CI ${ppInterval(r.ci_low, r.ci_high)}).`
    : `Across the ${players}, there is no detectable league-wide effect after ${k} makes in a row (effect ${pp(r.effect)}, 95% CI ${ppInterval(r.ci_low, r.ci_high)}).`;
  const individual =
    n === 0
      ? `No individual player shows a detectable hot or cold hand after accounting for testing ${int(r.n_players)} players.`
      : `${n} player${n > 1 ? "s show" : " shows"} a detectable effect after accounting for testing ${int(r.n_players)} players (${r.discoveries_hot} hot, ${r.discoveries_cold} cold).`;
  return `${overall} ${individual}`;
}

function putbackNote(league: League, k: number): string {
  const main = league.ks.find((r) => r.k === k);
  const np = league.no_putbacks?.find((r) => r.k === k);
  if (!main || !np) return "";
  return `<li>Putbacks and tip-ins mostly follow misses and go in often, but they explain only part of it: without them, the effect after ${k} makes in a row is ${pp(np.effect)} (95% CI ${ppInterval(np.ci_low, np.ci_high)}) instead of ${pp(main.effect)}.</li>`;
}

export async function renderHome(app: HTMLElement, go: (id: number) => void): Promise<void> {
  const [index, league] = await Promise.all([loadIndex(), loadLeague()]);
  document.title = "Is the Hot Hand Real?";
  const headline = 3;

  app.innerHTML = `
    <h1 tabindex="-1">Is the hot hand real?</h1>
    <p class="lede">When an NBA player makes a few shots in a row, is their next shot more likely to go in?
      We test every player's ${esc(league.season)} regular season, shot by shot, after removing statistical
      biases that make the obvious comparison misleading.</p>
    <div id="search-slot"></div>
    <p class="muted small">${int(league.n_players)} players are searchable; the ${int(league.n_tested)} with at least ${league.min_fga} attempts get the full test.</p>

    <h2>The league, ${esc(league.season)}</h2>
    <div class="tiles">
      ${league.ks
        .map(
          (r) => `
        <div class="tile">
          <div class="label">${streakName(r.k)}</div>
          <div class="value">${pp(r.effect)}</div>
          <div class="sub">95% CI ${ppInterval(r.ci_low, r.ci_high)} · ${pText(r.p_value, 10000)}</div>
          <div class="sub">${r.discoveries_hot + r.discoveries_cold} of ${int(r.n_players)} players with a detectable effect</div>
        </div>`,
        )
        .join("")}
    </div>
    <p>${leagueSentence(league, headline)}</p>

    <div class="callout">
      <strong>What this does and doesn't show.</strong>
      <ul>
        <li>The numbers compare a player's shots after makes with their shots after misses <em>in the same game</em>, minus the difference that luck alone would produce.</li>
        <li>A negative value doesn't mean "cold hands" in ability. After making shots, players may take harder shots and defenders may tighten up. We don't adjust for shot difficulty yet.</li>
        ${putbackNote(league, headline)}
        <li>"No detectable effect" is not the same as "no hot hand": with one season of shots, only large effects can be detected for a single player.</li>
      </ul>
    </div>

    <h2>Every tested player</h2>
    <p class="muted small">Each dot is one player's bias-corrected effect with its 95% confidence interval. Hover for details; click a dot to open the player.</p>
    <div class="segmented" role="group" aria-label="Streak length">
      ${league.ks.map((r) => `<button type="button" data-k="${r.k}" aria-pressed="${r.k === headline}">${r.k} make${r.k > 1 ? "s" : ""}</button>`).join("")}
    </div>
    <figure>
      <div class="legend">
        <span><span class="key" style="background: var(--neutral)"></span>no detectable effect</span>
        <span><span class="key" style="background: var(--hot)"></span>detectable hot hand</span>
        <span><span class="key" style="background: var(--cold)"></span>detectable cold hand</span>
        <span><span class="key line"></span>league-wide estimate (shaded: 95% CI)</span>
      </div>
      <div class="chart" id="league-chart"></div>
      <figcaption id="league-caption"></figcaption>
    </figure>
    <details>
      <summary>Show as a table</summary>
      <div class="table-wrap" id="league-table"></div>
    </details>`;

  app.querySelector("#search-slot")!.replaceWith(searchBox(index.players, go));

  const show = (k: number) => {
    const players = league.players.filter((p) => p.k === k);
    const lk = league.ks.find((r) => r.k === k)!;
    app.querySelectorAll<HTMLButtonElement>(".segmented button").forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.k) === k)));
    mountChart(app.querySelector("#league-chart")!, leagueChart(players, lk, k, go));
    app.querySelector("#league-caption")!.textContent = `${streakName(k)}: effect for ${players.length} players, sorted from lowest to highest. League-wide estimate ${pp(lk.effect)} (95% CI ${ppInterval(lk.ci_low, lk.ci_high)}).`;
    const sorted = [...players].sort((a, b) => b.effect - a.effect);
    app.querySelector("#league-table")!.innerHTML = `
      <table>
        <thead><tr><th>Player</th><th>FGA</th><th>Effect</th><th>95% CI</th><th>q-value</th><th>Result</th></tr></thead>
        <tbody>${sorted
          .map(
            (p) => `<tr><td><a href="#/player/${p.id}">${esc(p.name)}</a></td><td>${int(p.fga)}</td><td>${pp(p.effect)}</td>
              <td>${ppInterval(p.ci_low, p.ci_high)}</td><td>${p.q_value.toFixed(2)}</td>
              <td>${p.discovery ? (p.effect > 0 ? "hot hand" : "cold hand") : "no detectable effect"}</td></tr>`,
          )
          .join("")}</tbody>
      </table>`;
  };
  app.querySelectorAll<HTMLButtonElement>(".segmented button").forEach((b) => b.addEventListener("click", () => show(Number(b.dataset.k))));
  show(headline);
}
