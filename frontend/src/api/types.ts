export interface Team {
  id: number;
  name: string;
  logo_url: string | null;
  status: string;
}

export interface Game {
  id: number;
  season_id: number;
  game_date: string;
  start_time: string | null;
  venue: string | null;
  game_type: string;
  home_team_id: number;
  away_team_id: number;
  status: string;
  line_score: Record<string, unknown> | null;
  code: string | null;
  finalized_at: string | null;
}

export interface BoxscoreBattingRow {
  order: number | null;
  sub: number;
  player_id: number;
  name: string;
  pos: string | null;
  ab: number;
  r: number;
  h: number;
  rbi: number;
  bb: number;
  so: number;
  avg: string;
}

export interface BoxscoreBattingNotes {
  "2B": string[];
  "3B": string[];
  HR: string[];
  SB: string[];
  LOB: number | null;
}

export interface BoxscorePitchingRow {
  player_id: number;
  name: string;
  ip: string;
  h: number;
  r: number;
  er: number;
  bb: number;
  so: number;
  hr: number;
  era: string;
  decision: string | null;
}

export interface BoxscoreTeamSide {
  team: { id: number; name: string; logo_url: string | null };
  batting: BoxscoreBattingRow[];
  batting_notes: BoxscoreBattingNotes;
  pitching: BoxscorePitchingRow[];
}

export interface Boxscore {
  game: { id: number; date: string; venue: string | null; code: string | null; status: string };
  line_score: {
    home: number[];
    away: number[];
    home_totals: { r: number; h: number; e: number };
    away_totals: { r: number; h: number; e: number };
  };
  home: BoxscoreTeamSide;
  away: BoxscoreTeamSide;
}

export interface Season {
  id: number;
  year: number;
  name: string;
  innings_per_game: number;
  pa_qualifier_factor: string;
  ip_qualifier_factor: string;
  is_current: boolean;
}

export interface Player {
  id: number;
  team_id: number;
  name: string;
  number: number;
  positions: string | null;
  bats: string | null;
  throws: string | null;
  photo_url: string | null;
  status: string;
}

export interface BattingLine {
  player_id: number;
  bat_order: number | null;
  sub_index: number;
  pos: string | null;
  pa: number;
  ab: number;
  sh: number;
  sf: number;
  bb: number;
  hp: number;
  io: number;
  tie: number;
  r: number;
  h: number;
  b2: number;
  b3: number;
  hr: number;
  rbi: number;
  so: number;
  sb: number;
  cs: number;
  gidp: number;
  e: number;
}

export interface PitchingLine {
  player_id: number;
  seq: number;
  decision: string;
  outs: number;
  np: number;
  bf: number;
  ab: number;
  h: number;
  hr: number;
  bb: number;
  hp: number;
  so: number;
  r: number;
  er: number;
  wp: number;
  gs: boolean;
  cg: boolean;
  sho: boolean;
  sv: boolean;
  svo: boolean;
}

export interface ValidateCheck {
  name: string;
  ok: boolean;
  detail: string;
}

export interface ValidateResult {
  ok: boolean;
  checks: ValidateCheck[];
}

export interface GameLineScore {
  home: number[];
  away: number[];
  home_e?: number;
  away_e?: number;
  home_lob?: number;
  away_lob?: number;
}

export interface GameCreateInput {
  season_id: number;
  game_date: string;
  venue?: string;
  code?: string;
  home_team_id: number;
  away_team_id: number;
}
