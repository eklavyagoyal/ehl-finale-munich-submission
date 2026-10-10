import { AlertTriangle } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";

const STATUS_HINT: Record<number, string> = {
  401: "The frontend server is not authorised against the API. Check PARALLAX_API_TOKEN and the proxy.",
  403: "This action is reserved for a PM actor.",
  409: "A gate blocks this action.",
  422: "The input is not valid.",
  502: "The backend is not reachable from the frontend server.",
};

export function ErrorState({ error }: { error: unknown }) {
  const status = error instanceof ApiError ? error.status : undefined;
  const detail = error instanceof Error ? error.message : String(error);
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-100">
      <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div className="space-y-0.5">
        <p className="font-medium">
          {status === 401 && detail === "Sign in first"
            ? "Your session ended. Reload the page to sign in again."
            : status
              ? `${status} · ${STATUS_HINT[status] ?? "Request failed"}`
              : "Request failed"}
        </p>
        <p className="text-red-800/90 dark:text-red-200/90">{detail}</p>
      </div>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-2 border-t py-10 text-sm">
      <p className="font-medium">{title}</p>
      {children && <div className="max-w-prose text-muted-foreground">{children}</div>}
    </div>
  );
}

export function LoadingRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-3 py-4" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-4" style={{ width: `${55 + ((i * 17) % 35)}%` }} />
      ))}
    </div>
  );
}
