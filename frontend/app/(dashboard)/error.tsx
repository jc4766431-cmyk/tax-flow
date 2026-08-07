"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { AxiosError } from "axios";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  const message =
    error instanceof AxiosError
      ? (error.response?.data?.detail as string | undefined) ??
        "Something went wrong talking to the server."
      : error.message || "Something went wrong.";

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="max-w-md">
        <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--overdue-bg)] text-[var(--overdue)]">
            <AlertTriangle size={20} />
          </div>
          <div>
            <p className="font-[family-name:var(--font-display)] text-lg text-[var(--ink)]">
              This page couldn&apos;t load
            </p>
            <p className="mt-1 text-sm text-[var(--ink-muted)]">{message}</p>
          </div>
          <Button onClick={reset}>Try again</Button>
        </CardContent>
      </Card>
    </div>
  );
}
