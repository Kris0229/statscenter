import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { RequireAuth } from "./components/RequireAuth";
import { RequireRole } from "./components/RequireRole";
import { LeaguesPage } from "./pages/admin/LeaguesPage";
import { BoxscorePage } from "./pages/BoxscorePage";
import { GamesListPage } from "./pages/GamesListPage";
import { LoginPage } from "./pages/LoginPage";
import { NewGamePage } from "./pages/NewGamePage";
import { ReportPage } from "./pages/ReportPage";
import { SchedulePage } from "./pages/SchedulePage";
import { ScoreEntryPage } from "./pages/ScoreEntryPage";
import { TeamRosterPage } from "./pages/TeamRosterPage";
import { TeamsPage } from "./pages/TeamsPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/games" element={<GamesListPage />} />
        <Route path="/games/new" element={<NewGamePage />} />
        <Route path="/games/:gameId/score-entry" element={<ScoreEntryPage />} />
        <Route path="/games/:gameId/boxscore" element={<BoxscorePage />} />
        <Route path="/reports/:reportId" element={<ReportPage />} />
        <Route path="/teams" element={<TeamsPage />} />
        <Route path="/teams/:teamId" element={<TeamRosterPage />} />
        <Route path="/schedule" element={<SchedulePage />} />
        <Route
          path="/admin/leagues"
          element={
            <RequireRole roles={["super_admin"]}>
              <LeaguesPage />
            </RequireRole>
          }
        />
        <Route path="/" element={<Navigate to="/games" replace />} />
      </Route>
    </Routes>
  );
}
