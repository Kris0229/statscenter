import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useParams } from "react-router-dom";
import { Eye } from "lucide-react";

import {
  addPlayer,
  ApiError,
  createPlayerAccount,
  createTeamCaptainAccount,
  downloadRosterTemplate,
  fetchPlayerDetail,
  fetchTeam,
  fetchTeamPlayers,
  importRoster,
} from "@/api/client";
import type { ImportResult } from "@/api/types";
import { useMe } from "@/hooks/useMe";
import { PageHeader } from "@/components/PageHeader";
import { FormField } from "@/components/FormField";
import { FormError, FormSuccess } from "@/components/FormStatus";
import { LoadingBlock } from "@/components/Loading";
import { ConfirmDialog } from "@/components/ConfirmDialog";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const TITLE_LABELS: Record<string, string> = {
  manager: "領隊",
  coach: "教練",
  captain: "隊長",
  member: "隊員",
};

export function TeamRosterPage() {
  const { teamId: teamIdParam } = useParams();
  const teamId = Number(teamIdParam);
  const queryClient = useQueryClient();

  const meQuery = useMe();
  const teamQuery = useQuery({ queryKey: ["team", teamId], queryFn: () => fetchTeam(teamId) });
  const playersQuery = useQuery({
    queryKey: ["team", teamId, "players"],
    queryFn: () => fetchTeamPlayers(teamId),
  });

  const isAdmin = meQuery.data?.role === "admin";

  function refreshPlayers() {
    queryClient.invalidateQueries({ queryKey: ["team", teamId, "players"] });
  }
  function refreshTeam() {
    queryClient.invalidateQueries({ queryKey: ["team", teamId] });
  }

  // --- national_id on-demand reveal ---
  const [revealed, setRevealed] = useState<Record<number, string | null>>({});
  async function handleReveal(playerId: number) {
    const detail = await fetchPlayerDetail(playerId);
    setRevealed((prev) => ({ ...prev, [playerId]: detail.national_id }));
  }

  // --- captain account ---
  const [showCaptainForm, setShowCaptainForm] = useState(false);
  const [captainEmail, setCaptainEmail] = useState("");
  const [captainName, setCaptainName] = useState("");
  const [captainPassword, setCaptainPassword] = useState("");
  const [captainError, setCaptainError] = useState<string | null>(null);
  const [captainSubmitting, setCaptainSubmitting] = useState(false);

  async function handleCreateCaptain(e: FormEvent) {
    e.preventDefault();
    setCaptainError(null);
    setCaptainSubmitting(true);
    try {
      await createTeamCaptainAccount(teamId, {
        email: captainEmail, password: captainPassword, display_name: captainName,
      });
      setShowCaptainForm(false);
      setCaptainEmail("");
      setCaptainName("");
      setCaptainPassword("");
      refreshTeam();
    } catch (err) {
      setCaptainError(err instanceof ApiError ? err.message : "建立隊長帳號失敗");
    } finally {
      setCaptainSubmitting(false);
    }
  }

  // --- per-player account creation ---
  const [accountFormPlayerId, setAccountFormPlayerId] = useState<number | null>(null);
  const [accountEmail, setAccountEmail] = useState("");
  const [accountPassword, setAccountPassword] = useState("");
  const [accountError, setAccountError] = useState<string | null>(null);
  const [accountSubmitting, setAccountSubmitting] = useState(false);

  async function handleCreatePlayerAccount(e: FormEvent) {
    e.preventDefault();
    if (accountFormPlayerId === null) return;
    setAccountError(null);
    setAccountSubmitting(true);
    try {
      await createPlayerAccount(accountFormPlayerId, { email: accountEmail, password: accountPassword });
      setAccountFormPlayerId(null);
      setAccountEmail("");
      setAccountPassword("");
      refreshPlayers();
    } catch (err) {
      setAccountError(err instanceof ApiError ? err.message : "建立帳號失敗");
    } finally {
      setAccountSubmitting(false);
    }
  }

  // --- manual add player ---
  const [pName, setPName] = useState("");
  const [pNumber, setPNumber] = useState("");
  const [pPositions, setPPositions] = useState("");
  const [pTitle, setPTitle] = useState("member");
  const [pBirthdate, setPBirthdate] = useState("");
  const [pNationalId, setPNationalId] = useState("");
  const [pEmail, setPEmail] = useState("");
  const [pPhone, setPPhone] = useState("");
  const [addError, setAddError] = useState<string | null>(null);
  const [addSubmitting, setAddSubmitting] = useState(false);

  async function handleAddPlayer(e: FormEvent) {
    e.preventDefault();
    setAddError(null);
    setAddSubmitting(true);
    try {
      await addPlayer(teamId, {
        name: pName,
        number: Number(pNumber),
        positions: pPositions || undefined,
        title: pTitle,
        birthdate: pBirthdate || undefined,
        national_id: pNationalId || undefined,
        email: pEmail || undefined,
        phone: pPhone || undefined,
      });
      setPName("");
      setPNumber("");
      setPPositions("");
      setPTitle("member");
      setPBirthdate("");
      setPNationalId("");
      setPEmail("");
      setPPhone("");
      refreshPlayers();
    } catch (err) {
      setAddError(err instanceof ApiError ? err.message : "新增球員失敗");
    } finally {
      setAddSubmitting(false);
    }
  }

  // --- excel import ---
  const [importMode, setImportMode] = useState<"append" | "replace">("append");
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  async function handleImportFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportError(null);
    setImportResult(null);
    setImportBusy(true);
    try {
      const result = await importRoster(teamId, file, { mode: importMode });
      setImportResult(result);
      if (result.committed) {
        refreshPlayers();
        setPendingFile(null);
      } else if (result.errors.length === 0) {
        // replace mode preview — needs a second confirm call
        setPendingFile(file);
      }
    } catch (err) {
      setImportError(err instanceof ApiError ? err.message : "匯入失敗");
    } finally {
      setImportBusy(false);
      e.target.value = "";
    }
  }

  async function handleConfirmReplace() {
    if (!pendingFile) return;
    setImportBusy(true);
    setImportError(null);
    try {
      const result = await importRoster(teamId, pendingFile, { mode: "replace", confirm: true });
      setImportResult(result);
      setPendingFile(null);
      refreshPlayers();
    } catch (err) {
      setImportError(err instanceof ApiError ? err.message : "匯入失敗");
    } finally {
      setImportBusy(false);
    }
  }

  if (teamQuery.isLoading || playersQuery.isLoading) return <LoadingBlock />;

  const team = teamQuery.data;

  return (
    <div className="max-w-4xl">
      <PageHeader
        title={team?.name ?? ""}
        action={
          isAdmin ? (
            team?.captain_user_id ? (
              <span className="text-sm text-muted-foreground">此球隊已有隊長帳號。</span>
            ) : (
              <Button type="button" variant="outline" onClick={() => setShowCaptainForm(true)}>
                建立隊長帳號
              </Button>
            )
          ) : undefined
        }
      />

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>球員名單</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>背號</TableHead>
                <TableHead>姓名</TableHead>
                <TableHead>職稱</TableHead>
                <TableHead>守位</TableHead>
                <TableHead>生日</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>電話</TableHead>
                <TableHead>身分證字號</TableHead>
                {isAdmin && <TableHead>帳號</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {playersQuery.data?.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>{p.number}</TableCell>
                  <TableCell>{p.name}</TableCell>
                  <TableCell>{TITLE_LABELS[p.title] ?? p.title}</TableCell>
                  <TableCell>{p.positions ?? ""}</TableCell>
                  <TableCell>{p.birthdate ?? ""}</TableCell>
                  <TableCell>{p.email ?? ""}</TableCell>
                  <TableCell>{p.phone ?? ""}</TableCell>
                  <TableCell>
                    {revealed[p.id] !== undefined ? (
                      revealed[p.id] ?? "(未填)"
                    ) : (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => handleReveal(p.id)}
                      >
                        <Eye />
                        顯示
                      </Button>
                    )}
                  </TableCell>
                  {isAdmin && (
                    <TableCell>
                      {p.user_id ? (
                        <span className="text-sm text-muted-foreground">已建立</span>
                      ) : (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setAccountFormPlayerId(p.id);
                            setAccountError(null);
                          }}
                        >
                          建立登入帳號
                        </Button>
                      )}
                    </TableCell>
                  )}
                </TableRow>
              ))}
              {playersQuery.data?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={isAdmin ? 9 : 8} className="text-center text-muted-foreground">
                    尚無球員。
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {isAdmin && (
        <>
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>手動新增球員</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleAddPlayer} className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <FormField label="姓名" htmlFor="p-name" required>
                  <Input id="p-name" value={pName} onChange={(e) => setPName(e.target.value)} required />
                </FormField>
                <FormField label="背號" htmlFor="p-number" required>
                  <Input
                    id="p-number"
                    type="number"
                    value={pNumber}
                    onChange={(e) => setPNumber(e.target.value)}
                    required
                  />
                </FormField>
                <FormField label="守位" htmlFor="p-positions">
                  <Input id="p-positions" value={pPositions} onChange={(e) => setPPositions(e.target.value)} />
                </FormField>
                <FormField label="職稱" htmlFor="p-title">
                  <Select value={pTitle} onValueChange={setPTitle}>
                    <SelectTrigger id="p-title" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(TITLE_LABELS).map(([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
                <FormField label="生日" htmlFor="p-birthdate">
                  <Input
                    id="p-birthdate"
                    type="date"
                    value={pBirthdate}
                    onChange={(e) => setPBirthdate(e.target.value)}
                  />
                </FormField>
                <FormField label="身分證字號" htmlFor="p-national-id">
                  <Input
                    id="p-national-id"
                    value={pNationalId}
                    onChange={(e) => setPNationalId(e.target.value)}
                  />
                </FormField>
                <FormField label="Email" htmlFor="p-email">
                  <Input id="p-email" type="email" value={pEmail} onChange={(e) => setPEmail(e.target.value)} />
                </FormField>
                <FormField label="電話" htmlFor="p-phone">
                  <Input id="p-phone" value={pPhone} onChange={(e) => setPPhone(e.target.value)} />
                </FormField>
                <div className="col-span-2 sm:col-span-4">
                  <Button type="submit" disabled={addSubmitting}>
                    {addSubmitting ? "新增中…" : "新增球員"}
                  </Button>
                </div>
              </form>
              <FormError message={addError} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Excel 匯入球員名單</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-3 flex flex-wrap items-center gap-3">
                <Button type="button" variant="outline" onClick={() => downloadRosterTemplate(teamId)}>
                  下載範本
                </Button>
                <Select value={importMode} onValueChange={(v) => setImportMode(v as "append" | "replace")}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="append">附加（保留原名單）</SelectItem>
                    <SelectItem value="replace">取代（原名單設為離隊）</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  type="file"
                  accept=".xlsx"
                  onChange={handleImportFile}
                  disabled={importBusy}
                  className="max-w-xs"
                />
              </div>
              <FormError message={importError} />
              {importResult && importResult.errors.length > 0 && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>列</TableHead>
                      <TableHead>欄位</TableHead>
                      <TableHead>錯誤</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {importResult.errors.map((e, i) => (
                      <TableRow key={i}>
                        <TableCell>{e.row}</TableCell>
                        <TableCell>{e.field}</TableCell>
                        <TableCell>{e.msg}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
              {importResult && importResult.committed && (
                <FormSuccess message={`匯入成功，共 ${importResult.valid_rows} 筆。`} />
              )}
            </CardContent>
          </Card>
        </>
      )}

      <Dialog open={showCaptainForm} onOpenChange={setShowCaptainForm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>建立隊長帳號</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateCaptain} className="grid gap-4">
            <FormField label="隊長 Email" htmlFor="captain-email" required>
              <Input
                id="captain-email"
                type="email"
                value={captainEmail}
                onChange={(e) => setCaptainEmail(e.target.value)}
                required
              />
            </FormField>
            <FormField label="姓名" htmlFor="captain-name" required>
              <Input
                id="captain-name"
                value={captainName}
                onChange={(e) => setCaptainName(e.target.value)}
                required
              />
            </FormField>
            <FormField label="初始密碼" htmlFor="captain-password" required>
              <Input
                id="captain-password"
                type="password"
                value={captainPassword}
                onChange={(e) => setCaptainPassword(e.target.value)}
                required
              />
            </FormField>
            <FormError message={captainError} />
            <Button type="submit" disabled={captainSubmitting}>
              {captainSubmitting ? "建立中…" : "建立"}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog
        open={accountFormPlayerId !== null}
        onOpenChange={(open) => {
          if (!open) setAccountFormPlayerId(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>為球員建立登入帳號</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreatePlayerAccount} className="grid gap-4">
            <FormField label="Email" htmlFor="account-email" required>
              <Input
                id="account-email"
                type="email"
                value={accountEmail}
                onChange={(e) => setAccountEmail(e.target.value)}
                required
              />
            </FormField>
            <FormField label="初始密碼" htmlFor="account-password" required>
              <Input
                id="account-password"
                type="password"
                value={accountPassword}
                onChange={(e) => setAccountPassword(e.target.value)}
                required
              />
            </FormField>
            <FormError message={accountError} />
            <Button type="submit" disabled={accountSubmitting}>
              {accountSubmitting ? "建立中…" : "建立"}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={pendingFile !== null}
        onOpenChange={(open) => {
          if (!open) setPendingFile(null);
        }}
        title="確認取代目前名單？"
        description={`預覽通過，共 ${importResult?.valid_rows ?? 0} 筆。此動作會將現有球員標記為離隊。`}
        confirmLabel="確認取代"
        onConfirm={handleConfirmReplace}
        busy={importBusy}
        destructive
      />
    </div>
  );
}
