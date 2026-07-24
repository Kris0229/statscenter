import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { fetchGames } from "@/api/client";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { LoadingBlock } from "@/components/Loading";
import { GameStatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { FormError } from "@/components/FormStatus";

export function GamesListPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["games"], queryFn: fetchGames });

  return (
    <div>
      <PageHeader
        title="賽程"
        action={
          <Button asChild>
            <Link to="/games/new">+ 新增比賽</Link>
          </Button>
        }
      />
      {isLoading && <LoadingBlock />}
      {isError && <FormError message="無法載入賽程" />}
      {data && data.length === 0 && <EmptyState message="目前沒有比賽。" />}
      {data && data.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>日期</TableHead>
              <TableHead>賽事代碼</TableHead>
              <TableHead>狀態</TableHead>
              <TableHead></TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((game) => (
              <TableRow key={game.id}>
                <TableCell>{game.game_date}</TableCell>
                <TableCell>{game.code ?? "—"}</TableCell>
                <TableCell>
                  <GameStatusBadge status={game.status} />
                </TableCell>
                <TableCell>
                  <Link to={`/games/${game.id}/score-entry`} className="text-primary hover:underline">
                    計分
                  </Link>
                </TableCell>
                <TableCell>
                  <Link to={`/games/${game.id}/boxscore`} className="text-primary hover:underline">
                    比賽紀錄表
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
