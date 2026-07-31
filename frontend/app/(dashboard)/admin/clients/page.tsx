"use client";

import { useEffect, useState } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import Link from "next/link";
import { Search, Users, ChevronLeft, ChevronRight, MessageCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/dashboard/empty-state";
import type { PaginatedClients } from "@/lib/types";

const PAGE_SIZE = 20;

function useClients(search: string, page: number) {
  return useQuery<PaginatedClients>({
    queryKey: ["clients", search, page],
    queryFn: async () =>
      (
        await api.get("/clients", {
          params: { search: search || undefined, page, page_size: PAGE_SIZE },
        })
      ).data,
    placeholderData: keepPreviousData,
  });
}

export default function ClientsPage() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  // Debounce the search box so we don't fire a request per keystroke.
  useEffect(() => {
    const timeout = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(timeout);
  }, [searchInput]);

  const { data, isLoading, isError, error, isFetching } = useClients(search, page);

  if (isError) throw error;

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--ink)]">
          Clients
        </h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Everyone your firm is currently filing on behalf of.
        </p>
      </div>

      <div className="relative max-w-sm">
        <Search
          size={16}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ink-faint)]"
        />
        <Input
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search by company name or PAN"
          className="pl-9"
        />
      </div>

      <Card className={isFetching ? "opacity-70 transition-opacity" : "transition-opacity"}>
        <CardContent className="p-0">
          {isLoading || !data ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : data.items.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={Users}
                title={search ? "No clients match that search" : "No clients yet"}
                description={
                  search
                    ? "Try a different company name or PAN."
                    : "Clients your firm adds will show up here."
                }
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--line)] text-xs uppercase tracking-wide text-[var(--ink-muted)]">
                    <th className="px-5 py-3 font-medium">Company</th>
                    <th className="px-5 py-3 font-medium">PAN</th>
                    <th className="px-5 py-3 font-medium">GSTIN</th>
                    <th className="px-5 py-3 font-medium">Accountant</th>
                    <th className="px-5 py-3 font-medium" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)]">
                  {data.items.map((client) => (
                    <tr key={client.id} className="hover:bg-[var(--surface-hover)]">
                      <td className="px-5 py-3 font-medium text-[var(--ink)]">
                        {client.company_name ?? "—"}
                      </td>
                      <td className="tabular px-5 py-3 text-[var(--ink-muted)]">
                        {client.pan_number ?? "—"}
                      </td>
                      <td className="tabular px-5 py-3 text-[var(--ink-muted)]">
                        {client.gstin ?? "—"}
                      </td>
                      <td className="px-5 py-3">
                        {client.assigned_accountant_id ? (
                          <Badge tone="verified">Assigned</Badge>
                        ) : (
                          <Badge tone="pending">Unassigned</Badge>
                        )}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <Link
                          href={`/admin/clients/${client.id}/messages`}
                          className="inline-flex items-center gap-1 text-xs font-medium text-[var(--brass)] hover:text-[var(--brass-hover)]"
                        >
                          <MessageCircle size={14} /> Messages
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {data && data.total > 0 && (
        <div className="flex items-center justify-between text-sm text-[var(--ink-muted)]">
          <p>
            <span className="tabular">
              {(data.page - 1) * data.page_size + 1}–
              {Math.min(data.page * data.page_size, data.total)}
            </span>{" "}
            of <span className="tabular">{data.total}</span> clients
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              <ChevronLeft size={14} /> Prev
            </Button>
            <span className="tabular px-1">
              {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              Next <ChevronRight size={14} />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
