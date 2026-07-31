"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { MessagePage } from "@/lib/types";

export function useMessageThread(clientId: string | null | undefined) {
  const queryClient = useQueryClient();

  const query = useQuery<MessagePage>({
    queryKey: ["messages", "thread", clientId],
    queryFn: async () =>
      (await api.get(`/messages/thread/${clientId}`, { params: { page_size: 100 } })).data,
    enabled: !!clientId,
    refetchInterval: 20_000,
  });

  async function sendMessage(recipientId: string, body: string) {
    if (!clientId) return;
    await api.post("/messages", { client_id: clientId, recipient_id: recipientId, body });
    queryClient.invalidateQueries({ queryKey: ["messages", "thread", clientId] });
  }

  async function markRead(messageId: string) {
    await api.patch(`/messages/${messageId}/read`);
    queryClient.invalidateQueries({ queryKey: ["messages", "thread", clientId] });
  }

  return { ...query, sendMessage, markRead };
}
