export interface Team {
  id: number;
  name: string;
  logo_url: string | null;
  captain_user_id: number | null;
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
  user_id: number | null;
  name: string;
  number: number;
  positions: string | null;
  bats: string | null;
  throws: string | null;
  photo_url: string | null;
  title: "manager" | "coach" | "captain" | "member";
  birthdate: string | null;
  email: string | null;
  phone: string | null;
  status: string;
}

export interface PlayerDetail extends Player {
  national_id: string | null;
}

export interface League {
  id: number;
  name: string;
  slug: string;
  logo_url: string | null;
  status: string;
  created_at: string;
}

export interface LeagueAdmin {
  id: number;
  email: string;
  display_name: string;
  role: string;
  league_id: number;
}

export interface ImportRowError {
  row: number;
  field: string;
  msg: string;
}

export interface ImportResult {
  valid_rows: number;
  errors: ImportRowError[];
  committed: boolean;
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
  start_time?: string;
  venue?: string;
  code?: string;
  home_team_id: number;
  away_team_id: number;
}

export interface Media {
  id: number;
  game_id: number | null;
  player_id: number | null;
  uploader_id: number;
  type: "photo" | "video" | "link";
  url: string;
  status: string;
  created_at: string;
}

export interface ReportHighlightEntry {
  player: string;
  count?: number;
  hits?: number;
  so?: number;
}

export interface ReportHighlights {
  home_team_name: string;
  away_team_name: string;
  home_score: number;
  away_score: number;
  winning_pitcher: string | null;
  losing_pitcher: string | null;
  save_pitcher: string | null;
  home_runs: ReportHighlightEntry[];
  multi_hit_batters: ReportHighlightEntry[];
  big_strikeout_pitchers: ReportHighlightEntry[];
}

export interface Report {
  id: number;
  game_id: number;
  title: string;
  content: string | null;
  cover_media_id: number | null;
  author_id: number;
  published_at: string | null;
}
