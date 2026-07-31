"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageThread } from "@/components/dashboard/message-thread";
import type { Client } from "@/lib/types";

function useClient(clientId: string) {
  return useQuery<Client>({
    queryKey: ["clients", clientId],
    queryFn: async () => (await api.get(`/clients/${clientId}`)).data,
  });
}

export default function ClientMessagesPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: client, isLoading, isError, error } = useClient(id);

  if (isError) throw error;

  return (
    <div className="space-y-6">
      <Link
        href="/admin/clients"
        className="inline-flex items-center gap-1 text-sm text-[var(--ink-muted)] hover:text-[var(--ink)]"
      >
        <ArrowLeft size={14} /> Back to clients
      </Link>

      <div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--ink)]">
          {isLoading || !client ? "Messages" : client.company_name ?? "Messages"}
        </h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Message thread with this client.
        </p>
      </div>

      {isLoading || !client ? (
        <Skeleton className="h-80 w-full" />
      ) : (
        <MessageThread clientId={client.id} recipientId={client.user_id} />
      )}
    </div>
  );
}
