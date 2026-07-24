import { CheckCircle2, CircleAlert } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";

export function FormError({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <Alert variant="destructive">
      <CircleAlert />
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

export function FormSuccess({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <Alert className="border-success/30 bg-success/10 text-success">
      <CheckCircle2 className="text-success" />
      <AlertDescription className="text-success">{message}</AlertDescription>
    </Alert>
  );
}
