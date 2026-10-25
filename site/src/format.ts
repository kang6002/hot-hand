// Number formatting and all user-facing wording about results.
// Rule (CLAUDE.md): say "no detectable effect", never "no hot hand".

import type { League, Player, PowerRow, Test } from "./data";

const MINUS = "−";

/** Proportion -> signed percentage points, e.g. -0.0203 -> "−2.0 pp". */
export function pp(x: number | null | undefined, digits = 1): string {
  if (x == null) return "–";
  const v = (100 * x).toFixed(digits);
  if (Number(v) === 0) return `0.${"0".repeat(digits)} pp`;
  return x > 0 ? `+${v} pp` : `${MINUS}${v.replace("-", "")} pp`;
}

/** Proportion -> percentage, e.g. 0.4624 -> "46.2%". */
export function pct(x: number | null | undefined, digits = 1): string {
  return x == null ? "–" : `${(100 * x).toFixed(digits)}%`;
}

/** CI in percentage points, e.g. "[−3.0, −1.0]". */
export function ppInterval(lo: number | null, hi: number | null): string {
  return `[${pp(lo).replace(" pp", "")}, ${pp(hi).replace(" pp", "")}]`;
}

export function pctInterval(lo: number | null, hi: number | null): string {
  return lo == null || hi == null ? "" : `${(100 * lo).toFixed(1)}–${(100 * hi).toFixed(1)}%`;
}

/** p-value with sensible precision; smallest reportable value depends on the number of shuffles. */
export function pValue(p: number, nShuffles?: number): string {
  if (nShuffles && p <= 1.5 / (nShuffles + 1)) return `< ${(2 / (nShuffles + 1)).toPrecision(1)}`;
  if (p < 0.001) return p.toPrecision(2);
  return p < 0.01 ? p.toFixed(3) : p.toFixed(2);
}

export const int = (n: number) => n.toLocaleString("en-US");

export type Verdict = "hot" | "cold" | "none";

export function verdict(test: Test | undefined): Verdict {
  if (!test || !test.discovery) return "none";
  return test.effect > 0 ? "hot" : "cold";
}

export const verdictLabel: Record<Verdict, string> = {
  hot: "Detectable hot hand",
  cold: "Detectable cold hand",
  none: "No detectable effect",
};

export function verdictBadge(v: Verdict): string {
  return `<span class="verdict ${v}">${verdictLabel[v]}</span>`;
}

const streakName = (k: number) => (k === 1 ? "a make" : `${k} makes in a row`);
const missName = (k: number) => (k === 1 ? "a miss" : `${k} misses in a row`);

/** Plain-English summary of a player's headline (k = 3) result. */
export function playerSummary(player: Player, nTested: number, headlineK = 3): string {
  const first = player.name.split(" ")[0];
  if (!player.tested) {
    return `${player.name} took ${int(player.fga)} shots in ${player.season}, fewer than the ${player.min_fga} we need for a reliable test. The raw shooting numbers below are shown for interest only; they are not corrected for bias and can't tell a hot hand from luck.`;
  }
  const r = player.ks.find((x) => x.k === headlineK)!;
  const t = r.test!;
  const direction = t.effect >= 0 ? "more" : "less";
  const size = `${(100 * Math.abs(t.effect)).toFixed(1)} percentage points`;
  const base = `After ${streakName(headlineK)}, ${first}'s next shot went in ${size} ${direction} often than after ${missName(headlineK)}, once the statistical bias is removed (95% CI ${ppInterval(t.ci_low, t.ci_high)}).`;
  const v = verdict(t);
  if (v === "none") {
    return `${base} That is within the range luck alone produces once we account for testing ${nTested} players: no detectable effect.`;
  }
  const what = v === "hot" ? "a detectable hot hand" : "a detectable cold hand (shooting worse after makes)";
  return `${base} This is ${what}: unlikely to be luck, even after accounting for testing ${nTested} players (q = ${t.q_value.toFixed(3)}).`;
}

/** "How big a hot hand could we have found?" from the simulated power curve. */
export function powerSentence(player: Player, league: League, k = 3, boost = 0.1): string | null {
  const rows = league.power.filter((r: PowerRow) => r.k === k && Math.abs(r.boost - boost) < 1e-9);
  if (!rows.length) return null;
  // nearest simulated shot count (on a log scale)
  const nearest = rows.reduce((a, b) =>
    Math.abs(Math.log(b.fga / player.fga)) < Math.abs(Math.log(a.fga / player.fga)) ? b : a,
  );
  const share = (x: number) => (x >= 0.995 ? "almost always" : x < 0.01 ? "almost never" : `${Math.round(100 * x)}% of the time`);
  return `How sensitive is this? In simulations of players with about ${int(nearest.fga)} shots, a hot hand that adds ${Math.round(100 * boost)} percentage points after ${streakName(k)} is detected ${share(nearest.power_05)} at the usual 5% level, and ${share(nearest.power_001)} at the stricter level needed when testing hundreds of players. Published estimates of real hot-hand effects are mostly smaller than that.`;
}

/** Escape text for use inside HTML. */
export function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

/** "p = 0.21" or "p < 0.0002" */
export function pText(p: number, nShuffles?: number): string {
  const s = pValue(p, nShuffles);
  return s.startsWith("<") ? `p ${s}` : `p = ${s}`;
}
