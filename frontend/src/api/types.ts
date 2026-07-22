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
