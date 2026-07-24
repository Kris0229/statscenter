import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError, bootstrapLeagueAdmin, createLeague, fetchLeagues } from "@/api/client";
import { PageHeader } from "@/components/PageHeader";
import { FormField } from "@/components/FormField";
import { FormError, FormSuccess } from "@/components/FormStatus";
import { LoadingBlock } from "@/components/Loading";
import { EntityStatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function LeaguesPage() {
  const queryClient = useQueryClient();
  const leaguesQuery = useQuery({ queryKey: ["admin", "leagues"], queryFn: fetchLeagues });

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [adminFormLeagueId, setAdminFormLeagueId] = useState<number | null>(null);
  const [adminEmail, setAdminEmail] = useState("");
  const [adminName, setAdminName] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [adminError, setAdminError] = useState<string | null>(null);
  const [adminSubmitting, setAdminSubmitting] = useState(false);
  const [adminSuccess, setAdminSuccess] = useState<string | null>(null);

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ["admin", "leagues"] });
  }

  async function handleCreateLeague(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createLeague({ name, slug });
      setName("");
      setSlug("");
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "建立聯盟失敗");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCreateAdmin(e: FormEvent) {
    e.preventDefault();
    if (adminFormLeagueId === null) return;
    setAdminError(null);
    setAdminSuccess(null);
    setAdminSubmitting(true);
    try {
      const created = await bootstrapLeagueAdmin(adminFormLeagueId, {
        email: adminEmail, display_name: adminName, password: adminPassword,
      });
      setAdminSuccess(`已建立管理員:${created.email}`);
      setAdminEmail("");
      setAdminName("");
      setAdminPassword("");
    } catch (err) {
      setAdminError(err instanceof ApiError ? err.message : "指派管理員失敗");
    } finally {
      setAdminSubmitting(false);
    }
  }

  if (leaguesQuery.isLoading) return <LoadingBlock />;

  const adminFormLeague = leaguesQuery.data?.find((l) => l.id === adminFormLeagueId);

  return (
    <div className="max-w-3xl">
      <PageHeader title="聯盟管理" />

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>新增聯盟</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreateLeague} className="flex flex-wrap items-end gap-3">
            <FormField label="聯盟名稱" htmlFor="league-name" required className="grid gap-1.5">
              <Input id="league-name" value={name} onChange={(e) => setName(e.target.value)} required />
            </FormField>
            <FormField label="Slug（英數/連字號）" htmlFor="league-slug" required className="grid gap-1.5">
              <Input id="league-slug" value={slug} onChange={(e) => setSlug(e.target.value)} required />
            </FormField>
            <Button type="submit" disabled={submitting}>
              {submitting ? "建立中…" : "建立"}
            </Button>
          </form>
          <FormError message={error} />
        </CardContent>
      </Card>

      <h2 className="mb-2 text-lg font-semibold text-foreground">聯盟列表</h2>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>名稱</TableHead>
            <TableHead>Slug</TableHead>
            <TableHead>狀態</TableHead>
            <TableHead></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {leaguesQuery.data?.map((league) => (
            <TableRow key={league.id}>
              <TableCell>{league.name}</TableCell>
              <TableCell>{league.slug}</TableCell>
              <TableCell>
                <EntityStatusBadge status={league.status} />
              </TableCell>
              <TableCell>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setAdminFormLeagueId(league.id);
                    setAdminError(null);
                    setAdminSuccess(null);
                  }}
                >
                  指派管理員
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog
        open={adminFormLeagueId !== null}
        onOpenChange={(open) => {
          if (!open) setAdminFormLeagueId(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>指派管理員 — {adminFormLeague?.name}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateAdmin} className="grid gap-4">
            <FormField label="Email" htmlFor="admin-email" required>
              <Input
                id="admin-email"
                type="email"
                value={adminEmail}
                onChange={(e) => setAdminEmail(e.target.value)}
                required
              />
            </FormField>
            <FormField label="姓名" htmlFor="admin-name" required>
              <Input id="admin-name" value={adminName} onChange={(e) => setAdminName(e.target.value)} required />
            </FormField>
            <FormField label="初始密碼" htmlFor="admin-password" required>
              <Input
                id="admin-password"
                type="password"
                value={adminPassword}
                onChange={(e) => setAdminPassword(e.target.value)}
                required
              />
            </FormField>
            <FormError message={adminError} />
            <FormSuccess message={adminSuccess} />
            <Button type="submit" disabled={adminSubmitting}>
              {adminSubmitting ? "建立中…" : "建立管理員帳號"}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
