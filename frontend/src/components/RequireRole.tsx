import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useMe } from "@/hooks/useMe";
import { LoadingBlock } from "@/components/Loading";

export function RequireRole({ roles, children }: { roles: string[]; children: ReactNode }) {
  const meQuery = useMe();

  if (meQuery.isLoading) return <LoadingBlock />;
  if (!meQuery.data || !roles.includes(meQuery.data.role)) {
    return <Navigate to="/games" replace />;
  }
  return <>{children}</>;
}
