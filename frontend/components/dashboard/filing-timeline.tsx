"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { StampSeal } from "@/components/ui/stamp-seal";
import { FILING_STAGES, type FilingRequest } from "@/lib/types";

/**
 * Stamped filing-history timeline (HANDOFF.md §3d/§4). Fetches the full
 * filing on demand (GET /filings/{id}) and renders the six FILING_STAGES,
 * marking every completed stage with the shared <StampSeal>, per the design
 * system's "one signature element" rule — no second stamp visual invented.
 */
export function FilingTimeline({ filingId }: { filingId: string }) {
  const { data, isLoading } = useQuery<FilingRequest>({
    queryKey: ["filing", filingId],
    queryFn: async () => (await api.get(`/filings/${filingId}`)).data,
  });

  if (isLoading || !data) {
    return (
      <div className="flex gap-4 py-4">
        <Skeleton className="h-16 w-16 rounded-full" />
        <Skeleton className="h-16 w-16 rounded-full" />
        <Skeleton className="h-16 w-16 rounded-full" />
      </div>
    );
  }

  const currentIndex = FILING_STAGES.findIndex((s) => s.key === data.stage);

  return (
    <div className="flex flex-wrap items-start gap-x-6 gap-y-4 py-4">
      {FILING_STAGES.map((s, i) => {
        const done = i <= currentIndex;
        const event = data.stage_history.find((e) => e.stage === s.key);
        return (
          <div key={s.key} className="flex w-20 flex-col items-center text-center">
            {done ? (
              <StampSeal size={56} label="" sublabel={s.label.slice(0, 10)} delay={i * 0.08} />
            ) : (
              <div className="flex h-14 w-14 items-center justify-center rounded-full border border-dashed border-[var(--line)] text-[var(--ink-muted)]">
                <span className="text-xs">{i + 1}</span>
              </div>
            )}
            <p className="mt-2 text-xs font-medium text-[var(--ink)]">{s.label}</p>
            {event && (
              <p className="tabular mt-0.5 text-[10px] text-[var(--ink-muted)]">
                {new Date(event.created_at).toLocaleDateString("en-IN")}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
