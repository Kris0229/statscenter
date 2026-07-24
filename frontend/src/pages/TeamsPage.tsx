import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import { ApiError, createTeam, fetchTeams } from "@/api/client";
import { PageHeader } from "@/components/PageHeader";
import { FormError } from "@/components/FormStatus";
import { EmptyState } from "@/components/EmptyState";
import { LoadingBlock } from "@/components/Loading";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function TeamsPage() {
  const queryClient = useQueryClient();
  const teamsQuery = useQuery({ queryKey: ["teams"], queryFn: fetchTeams });

  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createTeam({ name });
      setName("");
      queryClient.invalidateQueries({ queryKey: ["teams"] });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "建立球隊失敗");
    } finally {
      setSubmitting(false);
    }
  }

  if (teamsQuery.isLoading) return <LoadingBlock />;

  return (
    <div className="max-w-3xl">
      <PageHeader title="球隊" />

      <form onSubmit={handleSubmit} className="mb-6 flex gap-2">
        <Input
          placeholder="新增球隊名稱"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          className="flex-1"
        />
        <Button type="submit" disabled={submitting}>
          {submitting ? "建立中…" : "新增球隊"}
        </Button>
      </form>
      <FormError message={error} />

      {teamsQuery.data?.length === 0 ? (
        <EmptyState message="尚無球隊。" />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
          {teamsQuery.data?.map((team) => (
            <Link key={team.id} to={`/teams/${team.id}`}>
              <Card className="transition-colors hover:border-primary/50 hover:bg-muted/40">
                <CardContent className="flex items-center gap-3">
                  {team.logo_url ? (
                    <img
                      src={team.logo_url}
                      alt=""
                      className="size-10 rounded-full object-cover"
                    />
                  ) : (
                    <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-medium text-muted-foreground">
                      {team.name.slice(0, 2)}
                    </div>
                  )}
                  <span className="font-medium text-foreground">{team.name}</span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
