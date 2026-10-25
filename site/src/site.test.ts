// Tests for search and wording (run: npm test). Some run against the real data in public/data.

import { describe, expect, it } from "vitest";
import type { IndexEntry, League, Player } from "./data";
import { partialNote, pp, pText, pValue, playerSummary, powerSentence, verdict } from "./format";
import { normalize, searchPlayers } from "./search";
import indexJson from "../public/data/index.json";
import leagueJson from "../public/data/league.json";

const players = (indexJson as { players: IndexEntry[] }).players;
const league = leagueJson as League;
const playerFiles = import.meta.glob<Player>("../public/data/players/*.json", { eager: true, import: "default" });

describe("normalize", () => {
  it("removes accents and punctuation", () => {
    expect(normalize("Luka Dončić")).toBe("luka doncic");
    expect(normalize("Nikola Jokić")).toBe("nikola jokic");
    expect(normalize("D'Angelo Russell")).toBe("dangelo russell");
    expect(normalize("P.J. Washington")).toBe("pj washington");
    expect(normalize("Shai Gilgeous-Alexander")).toBe("shai gilgeous alexander");
    expect(normalize("Kristaps Porziņģis")).toBe("kristaps porzingis");
  });
});

describe("search", () => {
  it("finds players without accents and by partial words", () => {
    expect(searchPlayers(players, "doncic")[0]?.name).toBe("Luka Dončić");
    expect(searchPlayers(players, "gilg alex")[0]?.name).toBe("Shai Gilgeous-Alexander");
    expect(searchPlayers(players, "   ")).toEqual([]);
  });

  it("finds every player by their full name and by their last name", () => {
    for (const p of players) {
      expect(searchPlayers(players, p.name, 50).map((r) => r.id)).toContain(p.id);
      // Last names can be shared by many players (54 Williamses), so allow all matches
      const last = p.name.split(" ").at(-1)!;
      expect(searchPlayers(players, last, players.length).map((r) => r.id)).toContain(p.id);
    }
  });
});

describe("formatting", () => {
  it("formats percentage points with a real minus sign", () => {
    expect(pp(-0.0203)).toBe("−2.0 pp");
    expect(pp(0.0275)).toBe("+2.8 pp");
    expect(pp(0.0004)).toBe("0.0 pp");
    expect(pp(null)).toBe("–");
  });

  it("never reports a p-value below what the shuffles can resolve", () => {
    expect(pValue(1 / 10001, 10000)).toBe("< 0.0002");
    expect(pText(1 / 10001, 10000)).toBe("p < 0.0002");
    expect(pText(0.2105)).toBe("p = 0.21");
  });
});

describe("wording on every player page", () => {
  const all = Object.values(playerFiles);

  it("has a file for every searchable player", () => {
    expect(all.length).toBe(players.length);
  });

  it("never says 'no hot hand'; untested players are told why", () => {
    for (const p of all) {
      const text = playerSummary(p, league.n_tested).toLowerCase();
      expect(text).not.toMatch(/\bno hot hand\b/);
      if (!p.tested) expect(text).toContain("fewer than the 300");
      else if (verdict(p.ks[2].test) === "none") expect(text).toContain("no detectable effect");
    }
  });

  it("gives every tested player a power sentence", () => {
    for (const p of all.filter((x) => x.tested)) {
      expect(powerSentence(p, league)).toMatch(/simulations of players with (about )?[\d,]+ shots/);
    }
  });

  it("flags careers that began before shot data, and only those", () => {
    const byName = (n: string) => all.find((p) => p.name === n)!;
    expect(partialNote(byName("Michael Jordan"))).toContain("began before 1996-97");
    expect(partialNote(byName("Kevin Garnett"))).toContain("began before 1996-97");
    expect(partialNote(byName("Kobe Bryant"))).toBeNull();
    expect(partialNote(byName("LeBron James"))).toBeNull();
  });

  it("shows per-season results only as estimates (no significance fields)", () => {
    for (const p of all) {
      for (const s of p.seasons) {
        for (const k of s.ks ?? []) expect(Object.keys(k).sort()).toEqual(["ci_high", "ci_low", "effect", "k"]);
      }
    }
  });
});
