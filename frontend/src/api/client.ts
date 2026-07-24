import type {
  BattingLine,
  Boxscore,
  Game,
  GameCreateInput,
  GameLineScore,
  ImportResult,
  League,
  LeagueAdmin,
  Media,
  PitchingLine,
  Player,
  PlayerDetail,
  Report,
  ReportHighlights,
  Season,
  Team,
  ValidateResult,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
const API_ORIGIN = API_BASE_URL.replace(/\/api\/v1\/?$/, "");
const TOKEN_KEY = "sc_access_token";

/** Local-storage media URLs come back origin-relative (e.g. "/media/x.jpg");
 * Supabase/S3-backed ones are already absolute. */
export function resolveMediaUrl(url: string): string {
  return /^https?:\/\//.test(url) ? url : `${API_ORIGIN}${url}`;
}

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
  // FormData sets its own multipart boundary in the Content-Type header —
  // overriding it here would break the upload.
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
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

/** Downloads a binary response (e.g. a generated .xlsx template) that needs
 * the Authorization header — a plain <a href> can't carry it, so fetch as a
 * blob and trigger the save client-side. */
export async function downloadFile(path: string, filename: string): Promise<void> {
  const token = getToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE_URL}${path}`, { headers });
  if (!res.ok) {
    throw new ApiError(res.status, `download failed: ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
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

export function fetchGameMedia(gameId: number): Promise<Media[]> {
  return apiFetch<Media[]>(`/media?game_id=${gameId}`);
}

export function uploadPhoto(gameId: number, file: File): Promise<Media> {
  const form = new FormData();
  form.set("type", "photo");
  form.set("game_id", String(gameId));
  form.set("file", file);
  return apiFetch<Media>("/media", { method: "POST", body: form });
}

export function uploadMediaLink(
  gameId: number,
  type: "video" | "link",
  url: string,
): Promise<Media> {
  const form = new FormData();
  form.set("type", type);
  form.set("game_id", String(gameId));
  form.set("url", url);
  return apiFetch<Media>("/media", { method: "POST", body: form });
}

export function updateMediaStatus(mediaId: number, status: "active" | "inactive"): Promise<Media> {
  return apiFetch<Media>(`/media/${mediaId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function deleteMedia(mediaId: number): Promise<void> {
  return apiFetch<void>(`/media/${mediaId}`, { method: "DELETE" });
}

export function fetchReportHighlights(gameId: number): Promise<ReportHighlights> {
  return apiFetch<ReportHighlights>(`/games/${gameId}/report-highlights`);
}

export function fetchReportsForGame(gameId: number): Promise<Report[]> {
  return apiFetch<Report[]>(`/reports?game_id=${gameId}`);
}

export function fetchReport(reportId: number): Promise<Report> {
  return apiFetch<Report>(`/reports/${reportId}`);
}

export interface ReportCreateInput {
  game_id: number;
  title?: string;
  content?: string;
  cover_media_id?: number;
}

export function createReport(input: ReportCreateInput): Promise<Report> {
  return apiFetch<Report>("/reports", { method: "POST", body: JSON.stringify(input) });
}

export interface ReportUpdateInput {
  title?: string;
  content?: string;
  cover_media_id?: number | null;
}

export function updateReport(reportId: number, input: ReportUpdateInput): Promise<Report> {
  return apiFetch<Report>(`/reports/${reportId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function publishReport(reportId: number): Promise<Report> {
  return apiFetch<Report>(`/reports/${reportId}/publish`, { method: "POST" });
}

// --- Leagues (super_admin) ---

export function fetchLeagues(): Promise<League[]> {
  return apiFetch<League[]>("/admin/leagues");
}

export interface LeagueCreateInput {
  name: string;
  slug: string;
  logo_url?: string;
}

export function createLeague(input: LeagueCreateInput): Promise<League> {
  return apiFetch<League>("/admin/leagues", { method: "POST", body: JSON.stringify(input) });
}

export interface LeagueAdminCreateInput {
  email: string;
  display_name: string;
  password: string;
}

export function bootstrapLeagueAdmin(
  leagueId: number,
  input: LeagueAdminCreateInput,
): Promise<LeagueAdmin> {
  return apiFetch<LeagueAdmin>(`/admin/leagues/${leagueId}/admins`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function fetchLeagueAdmins(leagueId: number): Promise<LeagueAdmin[]> {
  return apiFetch<LeagueAdmin[]>(`/admin/leagues/${leagueId}/admins`);
}

// --- Teams & roster ---

export interface TeamCreateInput {
  name: string;
  logo_url?: string;
}

export function createTeam(input: TeamCreateInput): Promise<Team> {
  return apiFetch<Team>("/teams", { method: "POST", body: JSON.stringify(input) });
}

export interface PlayerCreateInput {
  name: string;
  number: number;
  positions?: string;
  bats?: string;
  throws?: string;
  title?: string;
  birthdate?: string;
  national_id?: string;
  email?: string;
  phone?: string;
}

export function addPlayer(teamId: number, input: PlayerCreateInput): Promise<Player> {
  return apiFetch<Player>(`/teams/${teamId}/players`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function fetchPlayerDetail(playerId: number): Promise<PlayerDetail> {
  return apiFetch<PlayerDetail>(`/players/${playerId}`);
}

export function downloadRosterTemplate(teamId: number): Promise<void> {
  return downloadFile(`/teams/${teamId}/roster/template.xlsx`, "roster_template.xlsx");
}

export function importRoster(
  teamId: number,
  file: File,
  options: { mode?: "append" | "replace"; confirm?: boolean } = {},
): Promise<ImportResult> {
  const form = new FormData();
  form.set("file", file);
  const params = new URLSearchParams();
  if (options.mode) params.set("mode", options.mode);
  if (options.confirm) params.set("confirm", "true");
  const qs = params.toString();
  return apiFetch<ImportResult>(`/teams/${teamId}/roster/import${qs ? `?${qs}` : ""}`, {
    method: "POST",
    body: form,
  });
}

// --- Accounts (power/user) ---

export interface TeamCaptainCreateInput {
  email: string;
  password: string;
  display_name: string;
}

export function createTeamCaptainAccount(
  teamId: number,
  input: TeamCaptainCreateInput,
): Promise<{ id: number; email: string; display_name: string; role: string }> {
  return apiFetch(`/teams/${teamId}/captain-account`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export interface PlayerAccountCreateInput {
  email: string;
  password: string;
}

export function createPlayerAccount(
  playerId: number,
  input: PlayerAccountCreateInput,
): Promise<{ id: number; email: string; display_name: string; role: string }> {
  return apiFetch(`/players/${playerId}/account`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

// --- Seasons & schedule ---

export interface SeasonCreateInput {
  year: number;
  name: string;
  is_current?: boolean;
}

export function createSeason(input: SeasonCreateInput): Promise<Season> {
  return apiFetch<Season>("/seasons", { method: "POST", body: JSON.stringify(input) });
}

export function downloadScheduleTemplate(seasonId: number): Promise<void> {
  return downloadFile(`/seasons/${seasonId}/games/template.xlsx`, "schedule_template.xlsx");
}

export function importSchedule(
  seasonId: number,
  file: File,
  confirm = false,
): Promise<ImportResult> {
  const form = new FormData();
  form.set("file", file);
  const qs = confirm ? "?confirm=true" : "";
  return apiFetch<ImportResult>(`/seasons/${seasonId}/games/import${qs}`, {
    method: "POST",
    body: form,
  });
}
