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

export interface SeasonK {
  k: number;
  effect: number;
  ci_low: number;
  ci_high: number;
}

/** One season of a player's career: estimate + CI only (no significance labels). */
export interface SeasonEntry {
  season: string;
  fga: number;
  games: number;
  fg_pct: number;
  tested: boolean;
  ks?: SeasonK[];
}

export interface Player {
  id: number;
  name: string;
  first_season: string;
  last_season: string;
  n_seasons: number;
  partial_career: boolean; // career began before shot-level data (data_start)
  data_start: string;
  fga: number;
  games: number;
  fg: { pct: number; ci_low: number; ci_high: number };
  tested: boolean;
  min_fga: number;
  fdr_q: number;
  ks: KResult[];
  seasons: SeasonEntry[];
}

/** Every shot: per season, per game (d = "MM-DD", s = "1" make / "0" miss in order). */
export type ShotLog = { season: string; games: { d: string; s: string }[] }[];

export interface IndexEntry {
  id: number;
  name: string;
  fga: number;
  tested: boolean;
  first: string;
  last: string;
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

export interface LeagueSeasonK {
  season: string;
  k: number;
  n_players: number;
  effect: number;
  ci_low: number;
  ci_high: number;
  p_value: number;
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

export interface Estimate {
  k: number;
  effect: number;
  ci_low: number;
  ci_high: number;
  p_value: number;
}

export interface League {
  first_season: string;
  last_season: string;
  min_fga: number;
  fdr_q: number;
  n_players: number;
  n_tested: number;
  n_shots: number;
  ks: LeagueK[];
  seasons: LeagueSeasonK[];
  power: PowerRow[];
  /** Putback check for one season: main result vs without putbacks and tip-ins (empty lists if not run) */
  putback_check: { season: string; main: Estimate[]; without: Estimate[] };
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

export const loadIndex = () => load<{ players: IndexEntry[] }>("index.json");
export const loadLeague = () => load<League>("league.json");
export const loadLeaguePlayers = () => load<LeaguePlayer[]>("league_players.json");
export const loadPlayer = (id: number) => load<Player>(`players/${id}.json`);
export const loadShots = (id: number) => load<ShotLog>(`shots/${id}.json`);
