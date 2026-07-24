import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const GAME_STATUS: Record<string, { label: string; className: string }> = {
  scheduled: { label: "未開賽", className: "border-border bg-transparent text-muted-foreground" },
  in_progress: { label: "進行中", className: "border-transparent bg-warning text-warning-foreground" },
  final: { label: "已完成", className: "border-transparent bg-success text-success-foreground" },
  postponed: { label: "延賽", className: "border-transparent bg-muted text-muted-foreground" },
  cancelled: { label: "取消", className: "border-transparent bg-destructive text-white" },
};

const ENTITY_STATUS: Record<string, { label: string; className: string }> = {
  active: { label: "啟用", className: "border-transparent bg-success text-success-foreground" },
  inactive: { label: "已隱藏", className: "border-border bg-transparent text-muted-foreground" },
};

interface StatusBadgeProps {
  className?: string;
}

export function GameStatusBadge({ status, className }: { status: string } & StatusBadgeProps) {
  const meta = GAME_STATUS[status] ?? { label: status, className: "border-border bg-transparent text-muted-foreground" };
  return (
    <Badge variant="outline" className={cn(meta.className, className)}>
      {meta.label}
    </Badge>
  );
}

export function EntityStatusBadge({ status, className }: { status: string } & StatusBadgeProps) {
  const meta = ENTITY_STATUS[status] ?? { label: status, className: "border-border bg-transparent text-muted-foreground" };
  return (
    <Badge variant="outline" className={cn(meta.className, className)}>
      {meta.label}
    </Badge>
  );
}

export function MediaStatusBadge({ status, className }: { status: string } & StatusBadgeProps) {
  if (status === "active") return null;
  return <EntityStatusBadge status={status} className={className} />;
}

export function ReportStatusBadge({ publishedAt, className }: { publishedAt: string | null } & StatusBadgeProps) {
  if (publishedAt) {
    return (
      <Badge variant="outline" className={cn("border-transparent bg-success text-success-foreground", className)}>
        已發佈
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className={cn("border-transparent bg-warning text-warning-foreground", className)}>
      草稿
    </Badge>
  );
}
