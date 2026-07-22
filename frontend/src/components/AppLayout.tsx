import type { CSSProperties } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function AppLayout() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div style={{ fontFamily: "system-ui, sans-serif" }}>
      <header className="no-print" style={topBarStyle}>
        <Link to="/games" style={{ color: "inherit", textDecoration: "none", fontWeight: 600 }}>
          棒壘聯盟成績管理系統
        </Link>
        {isAuthenticated && (
          <button type="button" onClick={handleLogout} style={logoutButtonStyle}>
            登出
          </button>
        )}
      </header>
      <main style={{ padding: "1.5rem" }}>
        <Outlet />
      </main>
    </div>
  );
}

const topBarStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "0.75rem 1.5rem",
  borderBottom: "1px solid #ddd",
};

const logoutButtonStyle: CSSProperties = {
  border: "1px solid #ccc",
  background: "white",
  borderRadius: 4,
  padding: "0.35rem 0.75rem",
  cursor: "pointer",
};
