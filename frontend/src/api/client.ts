import type {
  BattingLine,
  Boxscore,
  Game,
  GameCreateInput,
  GameLineScore,
  PitchingLine,
  Player,
  Season,
  Team,
  ValidateResult,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
const TOKEN_KEY = "sc_access_token";

export class ApiError extends Error {
  status: number;
  code: string | undefined;

  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
  }
  if (!res.ok) {
    let detail = `request failed: ${res.status}`;
    let code: string | undefined;
    try {
      const body = (await res.json()) as { detail?: string; code?: string };
      detail = body.detail ?? detail;
      code = body.code;
    } catch {
      // response body wasn't JSON — keep the generic message
    }
    throw new ApiError(res.status, detail, code);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export interface HealthResponse {
  status: string;
}

export function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export async function login(email: string, password: string): Promise<void> {
  const body = await apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(body.access_token);
}

export function logout(): void {
  clearToken();
}

export interface CurrentUser {
  id: number;
  email: string;
  display_name: string;
  role: string;
  league_id: number | null;
  status: string;
}

export function fetchMe(): Promise<CurrentUser> {
  return apiFetch<CurrentUser>("/me");
}

export function fetchGames(): Promise<Game[]> {
  return apiFetch<Game[]>("/games");
}

export function fetchBoxscore(gameId: number): Promise<Boxscore> {
  return apiFetch<Boxscore>(`/games/${gameId}/boxscore`);
}

export function fetchGame(gameId: number): Promise<Game> {
  return apiFetch<Game>(`/games/${gameId}`);
}

export function fetchSeasons(): Promise<Season[]> {
  return apiFetch<Season[]>("/seasons");
}

export function fetchTeams(): Promise<Team[]> {
  return apiFetch<Team[]>("/teams");
}

export function fetchTeam(teamId: number): Promise<Team> {
  return apiFetch<Team>(`/teams/${teamId}`);
}

export function fetchTeamPlayers(teamId: number): Promise<Player[]> {
  return apiFetch<Player[]>(`/teams/${teamId}/players`);
}

export function createGame(input: GameCreateInput): Promise<Game> {
  return apiFetch<Game>("/games", { method: "POST", body: JSON.stringify(input) });
}

export function patchGameLineScore(gameId: number, lineScore: GameLineScore): Promise<Game> {
  return apiFetch<Game>(`/games/${gameId}`, {
    method: "PATCH",
    body: JSON.stringify({ line_score: lineScore }),
  });
}

export function fetchBattingLines(gameId: number): Promise<BattingLine[]> {
  return apiFetch<BattingLine[]>(`/games/${gameId}/batting`);
}

export function fetchPitchingLines(gameId: number): Promise<PitchingLine[]> {
  return apiFetch<PitchingLine[]>(`/games/${gameId}/pitching`);
}

export function putBattingLines(
  gameId: number,
  teamId: number,
  lines: BattingLine[],
): Promise<BattingLine[]> {
  return apiFetch<BattingLine[]>(`/games/${gameId}/batting`, {
    method: "PUT",
    body: JSON.stringify({ team_id: teamId, lines }),
  });
}

export function putPitchingLines(
  gameId: number,
  teamId: number,
  lines: PitchingLine[],
): Promise<PitchingLine[]> {
  return apiFetch<PitchingLine[]>(`/games/${gameId}/pitching`, {
    method: "PUT",
    body: JSON.stringify({ team_id: teamId, lines }),
  });
}

export function validateGame(gameId: number): Promise<ValidateResult> {
  return apiFetch<ValidateResult>(`/games/${gameId}/validate`, { method: "POST" });
}

export function finalizeGame(gameId: number): Promise<Game> {
  return apiFetch<Game>(`/games/${gameId}/finalize`, { method: "POST" });
}
