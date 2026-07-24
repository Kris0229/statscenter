import { useQuery } from "@tanstack/react-query";

import { fetchMe } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";

export function useMe() {
  const { isAuthenticated } = useAuth();
  return useQuery({ queryKey: ["me"], queryFn: fetchMe, enabled: isAuthenticated });
}
