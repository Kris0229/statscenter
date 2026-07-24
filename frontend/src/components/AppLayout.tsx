import { useQuery } from "@tanstack/react-query";
import type { CSSProperties } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";

import { fetchMe } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function AppLayout() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const meQuery = useQuery({ queryKey: ["me"], queryFn: fetchMe, enabled: isAuthenticated });

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const role = meQuery.data?.role;

  return (
    <div style={{ fontFamily: "system-ui, sans-serif" }}>
      <header className="no-print" style={topBarStyle}>
        <nav style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
          <Link to="/games" style={{ color: "inherit", textDecoration: "none", fontWeight: 600 }}>
            棒壘聯盟成績管理系統
          </Link>
          {isAuthenticated && role && role !== "super_admin" && (
            <>
              <Link to="/teams" style={navLinkStyle}>
                球隊
              </Link>
              <Link to="/schedule" style={navLinkStyle}>
                賽程管理
              </Link>
            </>
          )}
          {isAuthenticated && role === "super_admin" && (
            <Link to="/admin/leagues" style={navLinkStyle}>
              聯盟管理
            </Link>
          )}
        </nav>
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

const navLinkStyle: CSSProperties = {
  color: "inherit",
  textDecoration: "none",
  fontSize: "0.9rem",
};

const logoutButtonStyle: CSSProperties = {
  border: "1px solid #ccc",
  background: "white",
  borderRadius: 4,
  padding: "0.35rem 0.75rem",
  cursor: "pointer",
};
