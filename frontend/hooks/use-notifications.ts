"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, tokenStorage } from "@/lib/api";
import type { NotificationPage } from "@/lib/types";

export function useNotifications() {
  const queryClient = useQueryClient();

  const query = useQuery<NotificationPage>({
    queryKey: ["notifications"],
    queryFn: async () => (await api.get("/notifications", { params: { page_size: 20 } })).data,
    enabled: typeof window !== "undefined" && !!tokenStorage.getAccess(),
    refetchInterval: 60_000,
  });

  async function markRead(id: string) {
    await api.patch(`/notifications/${id}/read`);
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  }

  async function markAllRead() {
    await api.patch("/notifications/mark-all-read");
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  }

  const unreadCount = query.data?.items.filter((n) => !n.is_read).length ?? 0;

  return { ...query, unreadCount, markRead, markAllRead };
}
