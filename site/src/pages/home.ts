// Home: the all-time result in brief, and search.

import { loadIndex, loadLeague, type League } from "../data";
import { esc, int, pp, ppInterval, pText } from "../format";
import { searchBox } from "../search";

export const streakLabel = (k: number) => (k === 1 ? "After a make" : `After ${k} makes in a row`);

/** Plain-English league result for one k (all-time careers). */
export function leagueSentence(league: League, k: number): string {
  const r = league.ks.find((x) => x.k === k)!;
  const n = r.discoveries_hot + r.discoveries_cold;
  const players = `${int(r.n_players)} players with at least ${league.min_fga} career attempts (${league.first_season} to ${league.last_season})`;
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

/** "What this does and doesn't show" box, shared by home and league pages. */
export function caveats(league: League, k: number): string {
  const check = league.putback_check;
  const main = check?.main.find((r) => r.k === k);
  const without = check?.without.find((r) => r.k === k);
  const putbacks =
    main && without
      ? `<li>Putbacks and tip-ins mostly follow misses and go in often, but they explain only a small part of it: in ${esc(check.season)}, removing them changes the effect after ${k} makes in a row from ${pp(main.effect)} to ${pp(without.effect)} (95% CI ${ppInterval(without.ci_low, without.ci_high)}).</li>`
      : "";
  return `
    <div class="callout">
      <strong>What this does and doesn't show.</strong>
      <ul>
        <li>The numbers compare a player's shots after makes with their shots after misses <em>in the same game</em>, minus the difference that luck alone would produce.</li>
        <li>A negative value doesn't mean "cold hands" in ability. After making shots, players may take harder shots and defenders may tighten up. We don't adjust for shot difficulty yet.</li>
        ${putbacks}
        <li>"No detectable effect" is not the same as "no hot hand": small effects are hard to detect for a single player, even over a career. See <a href="#/method">how the test works</a>.</li>
      </ul>
    </div>`;
}

export function leagueTiles(league: League): string {
  return `
    <div class="tiles">
      ${league.ks
        .map(
          (r) => `
        <div class="tile">
          <div class="label">${streakLabel(r.k)}</div>
          <div class="value">${pp(r.effect)}</div>
          <div class="sub">95% CI ${ppInterval(r.ci_low, r.ci_high)} · ${pText(r.p_value, 10000)}</div>
          <div class="sub">${r.discoveries_hot + r.discoveries_cold} of ${int(r.n_players)} players with a detectable effect</div>
        </div>`,
        )
        .join("")}
    </div>`;
}

export async function renderHome(app: HTMLElement, go: (id: number) => void): Promise<void> {
  const [index, league] = await Promise.all([loadIndex(), loadLeague()]);
  document.title = "Is the Hot Hand Real?";
  const headline = 3;

  app.innerHTML = `
    <h1 tabindex="-1">Is the hot hand real?</h1>
    <p class="lede">When an NBA player makes a few shots in a row, is their next shot more likely to go in?
      We test every player's regular-season career since ${esc(league.first_season)}, shot by shot
      (${int(league.n_shots)} shots), after removing statistical biases that make the obvious comparison misleading.</p>
    <div id="search-slot"></div>
    <p class="muted small">${int(league.n_players)} players are searchable; the ${int(league.n_tested)} with at least ${league.min_fga} career attempts get the full test.</p>

    <h2>All players, ${esc(league.first_season)} to ${esc(league.last_season)}</h2>
    ${leagueTiles(league)}
    <p>${leagueSentence(league, headline)}</p>
    ${caveats(league, headline)}
    <p><a href="#/league">See every player and the season-by-season trend →</a></p>`;

  app.querySelector("#search-slot")!.replaceWith(searchBox(index.players, go));
}
