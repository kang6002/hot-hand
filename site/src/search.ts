// Accent-insensitive player search (ARIA combobox: arrow keys, Enter, Escape).

import type { IndexEntry } from "./data";
import { int } from "./format";

// Letters that don't decompose into base letter + accent
const SPECIAL: Record<string, string> = { ø: "o", ł: "l", đ: "d", æ: "ae", œ: "oe", ß: "ss", ı: "i" };

/** "Luka Dončić" -> "luka doncic" */
export function normalize(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[øłđæœßı]/g, (c) => SPECIAL[c])
    .replace(/['’.]/g, "") // "D'Angelo" -> "dangelo", "P.J." -> "pj"
    .replace(/[^a-z0-9 ]+/g, " ") // hyphens etc. split words: "gilgeous alexander"
    .replace(/\s+/g, " ")
    .trim();
}

/** Players whose name words start with every query word; best matches first. */
export function searchPlayers(players: IndexEntry[], query: string, limit = 8): IndexEntry[] {
  const words = normalize(query).split(" ").filter(Boolean);
  if (!words.length) return [];
  const scored: { p: IndexEntry; score: number }[] = [];
  for (const p of players) {
    const name = normalize(p.name);
    const tokens = name.split(" ");
    if (!words.every((w) => tokens.some((t) => t.startsWith(w)))) continue;
    // Prefer names that start with the query, then tested players, then more shots
    const score = (name.startsWith(words.join(" ")) ? 2e6 : 0) + (p.tested ? 1e6 : 0) + p.fga;
    scored.push({ p, score });
  }
  return scored.sort((a, b) => b.score - a.score).slice(0, limit).map((s) => s.p);
}

export function searchBox(players: IndexEntry[], onSelect: (id: number) => void): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "search";
  wrap.innerHTML = `
    <label for="player-search">Find a player</label>
    <input id="player-search" type="search" autocomplete="off" spellcheck="false"
      placeholder="e.g. Jokic, Curry, Gilgeous" role="combobox"
      aria-autocomplete="list" aria-expanded="false" aria-controls="player-results" />
    <ul id="player-results" role="listbox" aria-label="Matching players" hidden></ul>`;
  const input = wrap.querySelector("input")!;
  const list = wrap.querySelector("ul")!;
  let results: IndexEntry[] = [];
  let active = -1;

  const render = () => {
    list.replaceChildren(
      ...results.map((p, i) => {
        const li = document.createElement("li");
        li.id = `player-option-${p.id}`;
        li.setAttribute("role", "option");
        li.setAttribute("aria-selected", String(i === active));
        li.innerHTML = `<span></span><span class="meta">${int(p.fga)} FGA${p.tested ? "" : " · not tested"}</span>`;
        li.firstElementChild!.textContent = p.name;
        li.addEventListener("mousedown", (e) => {
          e.preventDefault(); // keep focus in the input
          onSelect(p.id);
        });
        return li;
      }),
    );
    const open = results.length > 0;
    list.hidden = !open;
    input.setAttribute("aria-expanded", String(open));
    if (active >= 0) input.setAttribute("aria-activedescendant", `player-option-${results[active].id}`);
    else input.removeAttribute("aria-activedescendant");
  };

  input.addEventListener("input", () => {
    results = searchPlayers(players, input.value);
    active = results.length ? 0 : -1;
    render();
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" && results.length) {
      active = (active + 1) % results.length;
      render();
      e.preventDefault();
    } else if (e.key === "ArrowUp" && results.length) {
      active = (active - 1 + results.length) % results.length;
      render();
      e.preventDefault();
    } else if (e.key === "Enter" && active >= 0) {
      onSelect(results[active].id);
      e.preventDefault();
    } else if (e.key === "Escape") {
      results = [];
      active = -1;
      render();
    }
  });
  input.addEventListener("blur", () => {
    results = [];
    active = -1;
    render();
  });
  return wrap;
}
