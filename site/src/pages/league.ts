// League page: all-time result, the trend season by season, and every tested player.

import { leagueChart, leagueSeasonsChart, mountChart } from "../charts";
import { loadLeague, loadLeaguePlayers } from "../data";
import { esc, int, pp, ppInterval, qText } from "../format";
import { caveats, leagueSentence, leagueTiles, streakLabel } from "./home";

function segmented(id: string, selected: number): string {
  return `
    <div class="segmented" role="group" aria-label="Streak length" id="${id}">
      ${[1, 2, 3].map((k) => `<button type="button" data-k="${k}" aria-pressed="${k === selected}">${k} make${k > 1 ? "s" : ""}</button>`).join("")}
    </div>`;
}

function onSegmented(app: HTMLElement, id: string, show: (k: number) => void): void {
  const group = app.querySelector<HTMLElement>(`#${id}`)!;
  group.querySelectorAll<HTMLButtonElement>("button").forEach((b) =>
    b.addEventListener("click", () => {
      group.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      show(Number(b.dataset.k));
    }),
  );
}

export async function renderLeague(app: HTMLElement, go: (id: number) => void): Promise<void> {
  const [league, players] = await Promise.all([loadLeague(), loadLeaguePlayers()]);
  document.title = "League · Is the Hot Hand Real?";
  const headline = 3;

  app.innerHTML = `
    <h1 tabindex="-1">The league, ${esc(league.first_season)} to ${esc(league.last_season)}</h1>
    <p class="lede">${leagueSentence(league, headline)}</p>
    ${leagueTiles(league)}
    ${caveats(league, headline)}

    <h2>Season by season</h2>
    <p class="muted small">The league-wide effect in each season (players with at least ${league.min_fga} attempts that season),
      as estimates with 95% confidence intervals. The solid line is the all-time estimate.</p>
    ${segmented("season-k", headline)}
    <figure>
      <div class="chart" id="seasons-chart"></div>
      <figcaption id="seasons-caption"></figcaption>
    </figure>
    <details><summary>Show as a table</summary><div class="table-wrap" id="seasons-table"></div></details>

    <h2>Every tested player (careers)</h2>
    <p class="muted small">Each dot is one player's bias-corrected career effect with its 95% confidence interval.
      Hover for details; click a dot to open the player.</p>
    ${segmented("players-k", headline)}
    <figure>
      <div class="legend">
        <span><span class="key" style="background: var(--neutral)"></span>no detectable effect</span>
        <span><span class="key" style="background: var(--hot)"></span>detectable hot hand</span>
        <span><span class="key" style="background: var(--cold)"></span>detectable cold hand</span>
        <span><span class="key line"></span>league-wide estimate (shaded: 95% CI)</span>
      </div>
      <div class="chart" id="players-chart"></div>
      <figcaption id="players-caption"></figcaption>
    </figure>
    <details><summary>Show as a table</summary><div class="table-wrap" id="players-table"></div></details>`;

  const showSeasons = (k: number) => {
    const allTime = league.ks.find((r) => r.k === k)!;
    const rows = league.seasons.filter((s) => s.k === k);
    mountChart(app.querySelector("#seasons-chart")!, leagueSeasonsChart(league.seasons, allTime, k));
    app.querySelector("#seasons-caption")!.textContent = `${streakLabel(k)}: league-wide effect by season, ${rows[0]?.season} to ${rows.at(-1)?.season}. All-time: ${pp(allTime.effect)}.`;
    app.querySelector("#seasons-table")!.innerHTML = `
      <table>
        <thead><tr><th>Season</th><th>Players</th><th>Effect</th><th>95% CI</th></tr></thead>
        <tbody>${rows.map((r) => `<tr><td>${r.season}</td><td>${int(r.n_players)}</td><td>${pp(r.effect)}</td><td>${ppInterval(r.ci_low, r.ci_high)}</td></tr>`).join("")}</tbody>
      </table>`;
  };

  const showPlayers = (k: number) => {
    const rows = players.filter((p) => p.k === k);
    const lk = league.ks.find((r) => r.k === k)!;
    mountChart(app.querySelector("#players-chart")!, leagueChart(rows, lk, k, go));
    app.querySelector("#players-caption")!.textContent = `${streakLabel(k)}: career effect for ${int(rows.length)} players, sorted from lowest to highest. League-wide estimate ${pp(lk.effect)} (95% CI ${ppInterval(lk.ci_low, lk.ci_high)}).`;
    const sorted = [...rows].sort((a, b) => b.effect - a.effect);
    app.querySelector("#players-table")!.innerHTML = `
      <table>
        <thead><tr><th>Player</th><th>FGA</th><th>Effect</th><th>95% CI</th><th>q-value</th><th>Result</th></tr></thead>
        <tbody>${sorted
          .map(
            (p) => `<tr><td><a href="#/player/${p.id}">${esc(p.name)}</a></td><td>${int(p.fga)}</td><td>${pp(p.effect)}</td>
              <td>${ppInterval(p.ci_low, p.ci_high)}</td><td>${qText(p.q_value)}</td>
              <td>${p.discovery ? (p.effect > 0 ? "hot hand" : "cold hand") : "no detectable effect"}</td></tr>`,
          )
          .join("")}</tbody>
      </table>`;
  };

  onSegmented(app, "season-k", showSeasons);
  onSegmented(app, "players-k", showPlayers);
  showSeasons(headline);
  showPlayers(headline);
}
