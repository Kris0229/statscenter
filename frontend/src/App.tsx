import { useQuery } from "@tanstack/react-query";

import { fetchHealth } from "./api/client";

export function App() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>棒壘聯盟成績管理系統</h1>
      <p>Phase 0 — scaffold</p>
      <section>
        <h2>API 健康檢查</h2>
        {isLoading && <p>檢查中…</p>}
        {isError && <p style={{ color: "crimson" }}>後端無法連線</p>}
        {data && (
          <p>
            後端狀態:<code>{data.status}</code>
          </p>
        )}
      </section>
    </main>
  );
}
