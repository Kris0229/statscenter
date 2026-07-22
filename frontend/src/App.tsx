import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { RequireAuth } from "./components/RequireAuth";
import { BoxscorePage } from "./pages/BoxscorePage";
import { GamesListPage } from "./pages/GamesListPage";
import { LoginPage } from "./pages/LoginPage";
import { NewGamePage } from "./pages/NewGamePage";
import { ScoreEntryPage } from "./pages/ScoreEntryPage";

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
        <Route path="/" element={<Navigate to="/games" replace />} />
      </Route>
    </Routes>
  );
}
