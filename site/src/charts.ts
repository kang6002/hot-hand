// Charts (Observable Plot ≈ ggplot2 for the web). Colours come from the CSS tokens in
// style.css, read when a chart is drawn; charts redraw on resize and theme change.

import * as Plot from "@observablehq/plot";
import type { KResult, LeaguePlayer, NullHist, Player } from "./data";
import { pct, pctInterval, pp, ppInterval, verdict } from "./format";

const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function baseStyle() {
  return {
    background: "transparent",
    color: css("--ink-2"),
    fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif",
    fontSize: "12px",
    overflow: "visible",
  };
}

// --- Mounting: draw at the container's width, redraw on resize / colour-scheme change ---

type Render = (width: number) => SVGSVGElement | HTMLElement;
const mounted = new Set<{ el: HTMLElement; render: Render }>();

export function mountChart(el: HTMLElement, render: Render): void {
  const entry = { el, render };
  const draw = () => {
    el.replaceChildren(render(Math.max(280, el.clientWidth)));
  };
  draw();
  mounted.add(entry);
  let lastWidth = el.clientWidth;
  const observer = new ResizeObserver(() => {
    if (!el.isConnected) {
      observer.disconnect();
      mounted.delete(entry);
    } else if (Math.abs(el.clientWidth - lastWidth) > 4) {
      lastWidth = el.clientWidth;
      draw();
    }
  });
  observer.observe(el);
}

function redrawAll(): void {
  for (const entry of mounted) {
    if (entry.el.isConnected) entry.el.replaceChildren(entry.render(Math.max(280, entry.el.clientWidth)));
    else mounted.delete(entry);
  }
}
// Redraw when the OS colour scheme changes or a data-theme attribute is set on <html>
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", redrawAll);
new MutationObserver(redrawAll).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

const verdictColor = (v: ReturnType<typeof verdict>) =>
  v === "hot" ? css("--hot") : v === "cold" ? css("--cold") : css("--neutral");

// --- Player: raw FG% after k makes / misses (not bias-corrected) ---

export function rawFgChart(player: Player): Render {
  const rows = player.ks.flatMap((r: KResult) =>
    (["makes", "misses"] as const).map((cond) => {
      const p = cond === "makes" ? r.after_makes : r.after_misses;
      return { k: `k = ${r.k}`, cond: `after ${cond}`, ...p };
    }),
  ).filter((d) => d.pct != null);
  const color = { domain: ["after makes", "after misses"], range: [css("--after-makes"), css("--after-misses")] };
  return (width) =>
    Plot.plot({
      width,
      height: 270,
      marginLeft: 44,
      marginTop: 34,
      style: baseStyle(),
      ariaLabel: `Raw field-goal percentage after 1, 2 and 3 makes and misses for ${player.name}`,
      fx: { label: null, padding: 0.15 },
      x: { label: null, padding: 0.4, tickFormat: (d: string) => d.replace("after ", "") },
      y: { label: "FG% (95% CI)", grid: true, tickFormat: (d: number) => `${Math.round(100 * d)}%`, nice: true },
      color,
      marks: [
        Plot.ruleY([player.fg.pct], { stroke: css("--ink-2"), strokeDasharray: "4 3" }),
        Plot.ruleX(rows, { fx: "k", x: "cond", y1: "ci_low", y2: "ci_high", stroke: "cond", strokeWidth: 2 }),
        Plot.dot(rows, {
          fx: "k", x: "cond", y: "pct", fill: "cond", r: 5, stroke: css("--surface"), strokeWidth: 1.5,
          tip: true,
          title: (d) => `${d.k}, ${d.cond}\nFG% ${pct(d.pct)} (95% CI ${pctInterval(d.ci_low, d.ci_high)})\n${d.n} shots`,
        }),
      ],
    });
}

// --- Player: bias-corrected effect with CI for k = 1, 2, 3 ---

export function effectsChart(player: Player): Render {
  const rows = player.ks
    .filter((r) => r.test)
    .map((r) => ({ k: `k = ${r.k}`, ...r.test!, v: verdict(r.test) }));
  return (width) =>
    Plot.plot({
      width,
      height: 150,
      marginLeft: 48,
      style: baseStyle(),
      ariaLabel: `Bias-corrected hot-hand effect with 95% confidence interval for ${player.name}, for 1, 2 and 3 makes in a row`,
      x: { label: "Bias-corrected effect (percentage points)", grid: true, nice: true, inset: 8, tickFormat: (d: number) => `${Math.round(100 * d)}` },
      y: { label: null, domain: rows.map((d) => d.k) },
      marks: [
        Plot.ruleX([0], { stroke: css("--ink-2"), strokeDasharray: "2 3" }),
        Plot.ruleY(rows, { y: "k", x1: "ci_low", x2: "ci_high", stroke: (d) => verdictColor(d.v), strokeWidth: 2 }),
        Plot.dot(rows, {
          y: "k", x: "effect", fill: (d) => verdictColor(d.v), r: 6, stroke: css("--surface"), strokeWidth: 1.5,
          tip: true,
          title: (d) => `${d.k}: effect ${pp(d.effect)}\n95% CI ${ppInterval(d.ci_low, d.ci_high)}\nq = ${d.q_value.toFixed(2)}`,
        }),
      ],
    });
}

// --- Player: shuffle (null) distribution with the observed raw difference ---

export function nullChart(hist: NullHist, dRaw: number, bias: number, k: number): Render {
  const bins = hist.counts.map((count, i) => ({
    x1: hist.start + i * hist.width,
    x2: hist.start + (i + 1) * hist.width,
    count,
  }));
  return (width) =>
    Plot.plot({
      width,
      height: 170,
      marginLeft: 12,
      style: baseStyle(),
      ariaLabel: `Distribution of the difference after ${k} makes minus after ${k} misses in ${hist.n} within-game shuffles, with the real value ${pp(dRaw)} and the shuffle mean ${pp(bias)}`,
      x: { label: "after makes − after misses (pp)", tickFormat: (d: number) => `${Math.round(100 * d)}`, nice: true },
      y: { axis: null },
      marks: [
        Plot.rectY(bins, { x1: "x1", x2: "x2", y: "count", fill: css("--null-fill"), insetLeft: 0.5, insetRight: 0.5 }),
        Plot.ruleX([bias], { stroke: css("--ink-2"), strokeDasharray: "4 3" }),
        Plot.ruleX([dRaw], { stroke: css("--ink"), strokeWidth: 2.5 }),
        Plot.ruleY([0], { stroke: css("--baseline") }),
      ],
    });
}

// --- Player: every shot of the season (rows = games, cells = shots) ---

export function gameLogChart(player: Player): Render {
  const cells = player.game_log.flatMap((g, row) => {
    let run = 0;
    return [...g.shots].map((s, i) => {
      const cell = { game: row, date: g.date, shot: i + 1, made: s === "1", run };
      run = s === "1" ? Math.max(run, 0) + 1 : Math.min(run, 0) - 1;
      return cell;
    });
  });
  const maxShots = Math.max(...player.game_log.map((g) => g.shots.length));
  const size = 11;
  const dates = player.game_log.map((g) => g.date);
  const fmtDate = (i: number) =>
    new Date(dates[i] + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const streak = (run: number) =>
    run > 0 ? `after ${run} make${run > 1 ? "s" : ""} in a row` : run < 0 ? `after ${-run} miss${run < -1 ? "es" : ""} in a row` : "first shot of the game";
  return () =>
    Plot.plot({
      width: 64 + maxShots * size + 16,
      height: 24 + player.game_log.length * size + 32,
      marginLeft: 64,
      marginTop: 24,
      style: baseStyle(),
      ariaLabel: `Every field-goal attempt by ${player.name} in ${player.season}: ${player.game_log.length} games, makes and misses in order`,
      x: { label: null, axis: "top", domain: Array.from({ length: maxShots }, (_, i) => i + 1), ticks: Array.from({ length: maxShots }, (_, i) => i + 1).filter((n) => n === 1 || n % 5 === 0), padding: 0.15 },
      y: { label: null, domain: dates.map((_, i) => i), tickFormat: fmtDate, ticks: dates.map((_, i) => i).filter((i) => i % 5 === 0), padding: 0.15 },
      marks: [
        Plot.cell(cells, {
          x: "shot", y: "game", rx: 2,
          fill: (d) => (d.made ? css("--shot-make") : css("--shot-miss")),
          tip: true,
          title: (d) => `${fmtDate(d.game)}, shot ${d.shot}: ${d.made ? "make" : "miss"}\n${streak(d.run)}`,
        }),
      ],
    });
}

// --- Home: every tested player's effect, sorted ---

export function leagueChart(players: LeaguePlayer[], leagueEffect: { effect: number; ci_low: number; ci_high: number }, k: number, onSelect: (id: number) => void): Render {
  const rows = [...players].sort((a, b) => a.effect - b.effect).map((d, i) => ({ ...d, rank: i + 1 }));
  return (width) => {
    const plot = Plot.plot({
      width,
      height: 340,
      marginLeft: 44,
      style: baseStyle(),
      ariaLabel: `Bias-corrected effect for ${rows.length} players after ${k} makes in a row, sorted from lowest to highest, with the league-wide estimate ${pp(leagueEffect.effect)}`,
      x: { label: `${rows.length} players, sorted by effect`, ticks: [] },
      y: { label: "Effect (pp) with 95% CI", grid: true, tickFormat: (d: number) => `${Math.round(100 * d)}` },
      marks: [
        Plot.rectY([leagueEffect], { x1: 0, x2: rows.length + 1, y1: "ci_low", y2: "ci_high", fill: css("--ink"), fillOpacity: 0.08 }),
        Plot.ruleY([0], { stroke: css("--ink-2"), strokeDasharray: "2 3" }),
        Plot.ruleY([leagueEffect.effect], { stroke: css("--ink"), strokeWidth: 1.5 }),
        Plot.ruleX(rows, { x: "rank", y1: "ci_low", y2: "ci_high", stroke: css("--baseline"), strokeWidth: 1 }),
        Plot.dot(rows, {
          x: "rank", y: "effect", r: 3,
          fill: (d) => verdictColor(d.discovery ? (d.effect > 0 ? "hot" : "cold") : "none"),
          tip: true,
          title: (d) => `${d.name} (${d.fga.toLocaleString("en-US")} FGA)\nEffect ${pp(d.effect)}, 95% CI ${ppInterval(d.ci_low, d.ci_high)}\n${d.discovery ? "BH discovery" : "No detectable effect"} · click to open`,
        }),
        Plot.text([leagueEffect], { x: rows.length, y: "ci_low", text: () => `league ${pp(leagueEffect.effect)}`, textAnchor: "end", dy: 10, fill: css("--ink"), stroke: css("--page"), strokeWidth: 4, fontSize: 12 }),
      ],
    });
    plot.style.cursor = "pointer";
    plot.addEventListener("click", () => {
      const v = (plot as unknown as { value: (typeof rows)[number] | null }).value;
      if (v) onSelect(v.id);
    });
    return plot;
  };
}
