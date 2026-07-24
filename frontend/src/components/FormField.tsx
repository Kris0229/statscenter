import type { ReactNode } from "react";

import { Label } from "@/components/ui/label";

interface FormFieldProps {
  label: string;
  htmlFor: string;
  required?: boolean;
  children: ReactNode;
  className?: string;
}

export function FormField({ label, htmlFor, required, children, className }: FormFieldProps) {
  return (
    <div className={className ?? "grid gap-1.5"}>
      <div className="flex items-center gap-1">
        <Label htmlFor={htmlFor}>{label}</Label>
        {required && (
          <span className="text-destructive" aria-hidden="true">
            *
          </span>
        )}
      </div>
      {children}
    </div>
  );
}
