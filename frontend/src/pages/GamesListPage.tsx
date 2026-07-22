import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { fetchGames } from "../api/client";

export function GamesListPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["games"], queryFn: fetchGames });

  return (
    <div>
      <h1>賽程</h1>
      {isLoading && <p>載入中…</p>}
      {isError && <p style={{ color: "crimson" }}>無法載入賽程</p>}
      {data && data.length === 0 && <p>目前沒有比賽。</p>}
      {data && data.length > 0 && (
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th style={thStyle}>日期</th>
              <th style={thStyle}>賽事代碼</th>
              <th style={thStyle}>狀態</th>
              <th style={thStyle}></th>
            </tr>
          </thead>
          <tbody>
            {data.map((game) => (
              <tr key={game.id}>
                <td style={tdStyle}>{game.game_date}</td>
                <td style={tdStyle}>{game.code ?? "—"}</td>
                <td style={tdStyle}>{game.status}</td>
                <td style={tdStyle}>
                  <Link to={`/games/${game.id}/boxscore`}>比賽紀錄表</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const thStyle = { textAlign: "left" as const, borderBottom: "2px solid #333", padding: "0.4rem" };
const tdStyle = { borderBottom: "1px solid #ddd", padding: "0.4rem" };
