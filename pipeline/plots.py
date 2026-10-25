"""Matplotlib figures for checking a season's results (Milestone 1).

Run from the project root (after analyse.py and power.py):
  .venv/bin/python pipeline/plots.py 2025-26 --players "Tyrese Maxey" "Shai Gilgeous-Alexander"
Output: figures/power_curve.png, figures/<season>/*.png
"""

import argparse
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # write files only, no window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyse import INTERIM_DIR, PROCESSED_DIR
from stats import KS

FIG_DIR = Path("figures")
ATTRIBUTION = "Data: NBA.com Stats via nba_api. Not affiliated with or endorsed by the NBA."

# Colours from the reference data-viz palette (light mode)
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
BLUE_RAMP = ["#86b6ef", "#3987e5", "#1c5cab"]   # ordered: small -> large hot hand
HOT, COLD = "#e34948", "#2a78d6"                 # diverging poles (hot = red, cold = blue)
AFTER_MAKES, AFTER_MISSES = "#2a78d6", "#eb6834"  # categorical slots 1 and 2

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "font.size": 10,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": BASELINE, "axes.labelcolor": INK_2, "axes.titlecolor": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK_2, "ytick.labelcolor": INK_2,
    "legend.frameon": False, "lines.linewidth": 2,
})


def finish(fig, path, note=""):
    """Add the attribution (and an optional note) and save."""
    fig.text(0.01, 0.01, (note + "   " if note else "") + ATTRIBUTION, fontsize=7.5, color=MUTED)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")


def plot_power_curve(path_csv=PROCESSED_DIR / "power_curve.csv"):
    power = pd.read_csv(path_csv)
    alphas = [c.removeprefix("power_") for c in power.columns if c.startswith("power_")]
    fig, axes = plt.subplots(len(alphas), len(KS), figsize=(12, 7), sharex=True, sharey=True)
    boosts = sorted(power["boost"].unique())
    for row, alpha in enumerate(alphas):
        for col, k in enumerate(KS):
            ax = axes[row, col]
            ends = []  # (y at the right end, label text), for direct labels
            for i, boost in enumerate(boosts):
                d = power[(power["k"] == k) & (power["boost"] == boost)].sort_values("fga")
                if boost == 0:
                    style = dict(color=MUTED, linestyle="--", linewidth=1.5, label="no hot hand")
                    text = "none"
                else:
                    style = dict(color=BLUE_RAMP[i - 1], marker="o", markersize=4,
                                 label=f"+{100 * boost:.0f} pp after {k} make{'s' * (k > 1)}")
                    text = f"+{100 * boost:.0f} pp"
                ax.plot(d["fga"], d[f"power_{alpha}"], **style)
                ends.append((d[f"power_{alpha}"].iloc[-1], text))
            # Direct labels only where they don't collide; the legend names every line
            last_y = np.inf
            for y, text in sorted(ends, reverse=True):
                if last_y - y >= 0.06:
                    ax.annotate(text, (power["fga"].max(), y), xytext=(6, 0), textcoords="offset points",
                                va="center", fontsize=8, color=INK_2)
                    last_y = y
            ax.axhline(0.8, color=BASELINE, linewidth=1)
            ax.axvspan(300, 1500, color=GRID, alpha=0.5, linewidth=0)
            ax.set_xscale("log")
            ax.set_xticks([300, 600, 1000, 1500, 3000, 6000], ["300", "600", "1k", "1.5k", "3k", "6k"])
            ax.minorticks_off()
            ax.set_ylim(0, 1.02)
            ax.set_title(f"k = {k}, α = {alpha}", loc="left", fontsize=10)
            if row == len(alphas) - 1:
                ax.set_xlabel("Field-goal attempts")
            if col == 0:
                ax.set_ylabel("Power (share detected)")
    axes[0, 0].text(320, 0.82, "80% power", fontsize=8, color=MUTED, va="bottom")
    axes[0, 0].text(320, 0.97, "one season", fontsize=8, color=MUTED, va="top")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, [re.sub(r" after .*", "", lab) + (" FG% after k makes" if "pp" in lab else "")
                         for lab in labels], loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle("How often the test detects a hot hand (simulated shooters)", x=0.01, ha="left", y=1.06)
    finish(fig, FIG_DIR / "power_curve.png",
           note=f"{int(power['n_sims'].iloc[0])} simulated players per point; 15 shots per game, base FG% 46%.")


def load_season(season):
    folder = PROCESSED_DIR / season
    players = pd.read_csv(folder / "players.csv")
    streaks = pd.read_csv(folder / "streaks.csv").merge(players[["player_id", "player_name", "fga"]], on="player_id")
    league = pd.read_csv(folder / "league.csv")
    draws = np.load(INTERIM_DIR / f"draws_{season}.npz")
    return players, streaks, league, draws


def plot_effects(season, streaks, league):
    fig, axes = plt.subplots(1, len(KS), figsize=(13, 4.5), sharey=True)
    for ax, k in zip(axes, KS):
        d = streaks[(streaks["k"] == k) & streaks["p_value"].notna()].sort_values("effect")
        x = np.arange(len(d))
        discovery = d["discovery"].astype(str).eq("True").to_numpy()
        colors = np.where(~discovery, MUTED, np.where(d["effect"] > 0, HOT, COLD))
        ax.vlines(x, 100 * d["ci_low"], 100 * d["ci_high"], color=BASELINE, linewidth=0.8)
        ax.scatter(x, 100 * d["effect"], c=colors, s=9, zorder=3)
        lg = league[league["k"] == k].iloc[0]
        ax.axhspan(100 * lg["ci_low"], 100 * lg["ci_high"], color=INK, alpha=0.08, linewidth=0)
        ax.axhline(100 * lg["effect"], color=INK, linewidth=1.2)
        ax.axhline(0, color=INK_2, linewidth=0.8, linestyle=":")
        ax.annotate(f"league {100 * lg['effect']:+.1f} pp", (len(d) * 0.97, 100 * lg["ci_low"]),
                    xytext=(0, -4), textcoords="offset points", ha="right", va="top", fontsize=8, color=INK)
        ax.set_xticks([])
        ax.set_xlabel(f"{len(d)} players, sorted by effect")
        n_disc = int(discovery.sum())
        ax.set_title(f"k = {k}: {n_disc} BH discover{'y' if n_disc == 1 else 'ies'}", loc="left", fontsize=10)
    axes[0].set_ylabel("Bias-corrected effect (pp) with 95% CI")
    fig.suptitle(f"Hot-hand effect for every tested player, {season} regular season (≥ 300 FGA)",
                 x=0.01, ha="left")
    finish(fig, FIG_DIR / season / "effects.png",
           note="Grey: no detectable effect after BH-FDR (q = 0.05). Red/blue would mark hot/cold discoveries.")


def plot_diagnostics(season, streaks):
    fig, axes = plt.subplots(2, len(KS), figsize=(12, 6.5))
    for col, k in enumerate(KS):
        d = streaks[(streaks["k"] == k) & streaks["p_value"].notna()]
        ax = axes[0, col]
        bins = np.linspace(0, 1, 21)
        ax.hist(d["p_value"], bins=bins, color=BLUE_RAMP[1], edgecolor=SURFACE, linewidth=1)
        ax.axhline(len(d) / 20, color=INK_2, linestyle="--", linewidth=1)
        ax.set_title(f"k = {k}: p-values (dashed = if no effects)", loc="left", fontsize=10)
        ax.set_xlabel("p-value")
        if col == 0:
            ax.set_ylabel("Players")

        ax = axes[1, col]
        ax.hist(100 * d["bias"], bins=25, color=MUTED, edgecolor=SURFACE, linewidth=1)
        ax.axvline(0, color=INK_2, linestyle=":", linewidth=1)
        ax.axvline(100 * d["bias"].median(), color=INK, linewidth=1.2)
        ax.set_title(f"k = {k}: bias removed (median {100 * d['bias'].median():+.1f} pp)", loc="left", fontsize=10)
        ax.set_xlabel("Shuffle mean = bias of the raw comparison (pp)")
        if col == 0:
            ax.set_ylabel("Players")
    fig.suptitle(f"Checks, {season}: p-value distribution and size of the bias correction", x=0.01, ha="left")
    fig.tight_layout()
    finish(fig, FIG_DIR / season / "diagnostics.png")


def plot_player(season, name, players, streaks, draws):
    match = players[players["player_name"] == name]
    if match.empty:
        print(f"No player called {name!r} in {season}")
        return
    p = match.iloc[0]
    rows = streaks[streaks["player_id"] == p["player_id"]].set_index("k")
    fig, axes = plt.subplots(1, 1 + len(KS), figsize=(14, 3.8), gridspec_kw={"width_ratios": [1.3, 1, 1, 1]})

    # A: raw FG% after k makes / misses (not bias-corrected)
    ax = axes[0]
    for offset, cond, color in [(-0.12, "makes", AFTER_MAKES), (0.12, "misses", AFTER_MISSES)]:
        x = np.array(KS) + offset
        pct = 100 * rows[f"pct_after_{cond}"]
        err = [pct - 100 * rows[f"ci_low_after_{cond}"], 100 * rows[f"ci_high_after_{cond}"] - pct]
        ax.errorbar(x, pct, yerr=err, fmt="o", color=color, markersize=6, capsize=0, elinewidth=1.5,
                    label=f"after k {cond}")
    ax.axhline(100 * p["fg_pct"], color=INK_2, linestyle="--", linewidth=1)
    ax.text(3.65, 100 * p["fg_pct"] + 0.4, "overall", fontsize=8, color=INK_2, ha="right", va="bottom")
    ax.set_xticks(KS, [f"k = {k}" for k in KS])
    ax.set_xlim(0.6, 3.7)
    ax.set_ylabel("FG% (95% Wilson CI)")
    ax.set_title("Raw FG% (not bias-corrected)", loc="left", fontsize=10)
    ax.legend(loc="lower left", fontsize=8)

    # B-D: shuffle (null) distribution with the observed raw difference
    if p["tested"]:
        index = int(np.flatnonzero(draws["player_id"] == p["player_id"])[0])
        for ax, k in zip(axes[1:], KS):
            r = rows.loc[k]
            null = 100 * draws[f"null_k{k}"][index]
            ax.hist(null[~np.isnan(null)], bins=40, color=GRID, edgecolor=SURFACE, linewidth=0.5)
            ax.axvline(100 * r["bias"], color=INK_2, linestyle="--", linewidth=1)
            ax.axvline(100 * r["d_raw"], color=INK, linewidth=2)
            verdict = ("detectable " + ("hot" if r["effect"] > 0 else "cold") + " hand"
                       if str(r["discovery"]) == "True" else "no detectable effect")
            ax.set_title(f"k = {k}: {verdict}", loc="left", fontsize=10)
            observed_left = 100 * r["d_raw"] < np.nanmean(null)
            ax.text(0.98 if observed_left else 0.02, 0.97,
                    f"effect {100 * r['effect']:+.1f} pp\n95% CI [{100 * r['ci_low']:+.1f}, {100 * r['ci_high']:+.1f}]\n"
                    f"p = {r['p_value']:.3g}, q = {r['q_value']:.2f}",
                    transform=ax.transAxes, fontsize=8, color=INK_2, va="top",
                    ha="right" if observed_left else "left",
                    bbox=dict(facecolor=SURFACE, edgecolor="none", alpha=0.9, pad=1.5))
            ax.set_xlabel("FG% after makes − after misses (pp)")
            ax.set_yticks([])
    else:
        for ax in axes[1:]:
            ax.axis("off")
        axes[2].text(0.5, 0.5, f"{p['fga']} FGA: not enough shots for a reliable test", ha="center", color=INK_2)

    fig.suptitle(f"{name}, {season}: {p['fga']} FGA in {p['games']} games, FG% {100 * p['fg_pct']:.1f}",
                 x=0.01, ha="left", y=0.99)
    fig.tight_layout()
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    finish(fig, FIG_DIR / season / f"player_{slug}.png",
           note="Right panels: grey = 10,000 within-game shuffles, dashed = their mean (the bias), "
                "solid = real games. Effect = solid − dashed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("season", nargs="?", default="2025-26")
    parser.add_argument("--players", nargs="*", default=["Tyrese Maxey", "Shai Gilgeous-Alexander"])
    args = parser.parse_args()

    if (PROCESSED_DIR / "power_curve.csv").exists():
        plot_power_curve()
    players, streaks, league, draws = load_season(args.season)
    plot_effects(args.season, streaks, league)
    plot_diagnostics(args.season, streaks)
    for name in args.players:
        plot_player(args.season, name, players, streaks, draws)


if __name__ == "__main__":
    main()
