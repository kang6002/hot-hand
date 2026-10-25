// Types mirroring the JSON written by pipeline/build_json.py, and cached loaders.

export interface Proportion {
  n: number;
  pct: number | null;
  ci_low: number | null;
  ci_high: number | null;
}

export interface NullHist {
  start: number;
  width: number;
  counts: number[];
  n: number;
}

export interface Test {
  d_raw: number;
  bias: number;
  effect: number;
  ci_low: number;
  ci_high: number;
  p_value: number;
  q_value: number;
  discovery: boolean;
  n_shuffles: number;
  null_hist: NullHist | null;
}

export interface KResult {
  k: number;
  after_makes: Proportion;
  after_misses: Proportion;
  test?: Test;
}

export interface Game {
  game_id: string;
  date: string;
  shots: string; // "1" = make, "0" = miss, in shot order
}

export interface Player {
  id: number;
  name: string;
  season: string;
  fga: number;
  games: number;
  fg: { pct: number; ci_low: number; ci_high: number };
  tested: boolean;
  min_fga: number;
  fdr_q: number;
  ks: KResult[];
  game_log: Game[];
}

export interface IndexEntry {
  id: number;
  name: string;
  fga: number;
  tested: boolean;
}

export interface LeagueK {
  k: number;
  n_players: number;
  effect: number;
  ci_low: number;
  ci_high: number;
  p_value: number;
  discoveries_hot: number;
  discoveries_cold: number;
}

export interface LeaguePlayer {
  id: number;
  name: string;
  fga: number;
  k: number;
  effect: number;
  ci_low: number;
  ci_high: number;
  q_value: number;
  discovery: boolean;
}

export interface PowerRow {
  k: number;
  fga: number;
  boost: number;
  power_05: number;
  power_001: number;
}

export interface League {
  season: string;
  min_fga: number;
  fdr_q: number;
  n_players: number;
  n_tested: number;
  ks: LeagueK[];
  players: LeaguePlayer[];
  power: PowerRow[];
  /** League result without putbacks and tip-ins (sensitivity check); empty if not run */
  no_putbacks: { k: number; effect: number; ci_low: number; ci_high: number; p_value: number }[];
}

const cache = new Map<string, Promise<unknown>>();

// Fetch a JSON file from public/data once; later calls reuse the same promise.
function load<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    const url = `${import.meta.env.BASE_URL}data/${path}`;
    cache.set(
      path,
      fetch(url).then((r) => {
        if (!r.ok) throw new Error(`${r.status} loading ${path}`);
        return r.json();
      }),
    );
  }
  return cache.get(path) as Promise<T>;
}

export const loadIndex = () => load<{ season: string; players: IndexEntry[] }>("index.json");
export const loadLeague = () => load<League>("league.json");
export const loadPlayer = (id: number) => load<Player>(`players/${id}.json`);
