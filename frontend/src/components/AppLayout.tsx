import { LogOut } from "lucide-react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { useMe } from "@/hooks/useMe";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

const ROLE_LABELS: Record<string, string> = {
  super_admin: "系統管理員",
  admin: "管理員",
  power: "進階使用者",
  user: "一般使用者",
};

function navLinkClassName({ isActive }: { isActive: boolean }) {
  return cn(
    "border-b-2 px-1 py-1 text-sm font-medium transition-colors",
    isActive
      ? "border-accent text-white"
      : "border-transparent text-white/70 hover:text-white",
  );
}

function initials(name: string) {
  return name.trim().slice(0, 2).toUpperCase();
}

export function AppLayout() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const meQuery = useMe();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const role = meQuery.data?.role;

  return (
    <div className="min-h-screen bg-background">
      <header className="no-print sticky top-0 z-40 flex items-center justify-between gap-4 bg-primary px-6 py-3 text-primary-foreground shadow-sm">
        <nav className="flex items-center gap-6">
          <Link to="/games" className="text-lg font-bold tracking-tight text-white">
            棒壘聯盟成績管理系統
          </Link>
          {isAuthenticated && role && role !== "super_admin" && (
            <div className="flex items-center gap-5">
              <NavLink to="/games" className={navLinkClassName}>
                比賽
              </NavLink>
              <NavLink to="/teams" className={navLinkClassName}>
                球隊
              </NavLink>
              <NavLink to="/schedule" className={navLinkClassName}>
                賽程管理
              </NavLink>
            </div>
          )}
          {isAuthenticated && role === "super_admin" && (
            <NavLink to="/admin/leagues" className={navLinkClassName}>
              聯盟管理
            </NavLink>
          )}
        </nav>
        {isAuthenticated && (
          <DropdownMenu>
            <DropdownMenuTrigger className="rounded-full outline-none ring-offset-primary focus-visible:ring-2 focus-visible:ring-white/50">
              <Avatar>
                <AvatarFallback className="bg-white/15 text-white">
                  {meQuery.data ? initials(meQuery.data.display_name) : "…"}
                </AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel className="flex flex-col">
                <span className="font-medium">{meQuery.data?.display_name}</span>
                <span className="text-xs font-normal text-muted-foreground">
                  {role ? (ROLE_LABELS[role] ?? role) : ""}
                </span>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive" onClick={handleLogout}>
                <LogOut />
                登出
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
