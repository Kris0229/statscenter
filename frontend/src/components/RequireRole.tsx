import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { fetchMe } from "../api/client";

export function RequireRole({ roles, children }: { roles: string[]; children: ReactNode }) {
  const meQuery = useQuery({ queryKey: ["me"], queryFn: fetchMe });

  if (meQuery.isLoading) return <p>載入中…</p>;
  if (!meQuery.data || !roles.includes(meQuery.data.role)) {
    return <Navigate to="/games" replace />;
  }
  return <>{children}</>;
}
