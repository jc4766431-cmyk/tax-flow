"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Client, PaginatedClients } from "@/lib/types";

/** Full client list for select/filter dropdowns and id->name lookups.
 * Uses the max page_size the API allows rather than paging through, which
 * is fine for a single firm's client roster in this product's scale. */
export function useClientsList() {
  return useQuery<PaginatedClients>({
    queryKey: ["clients", "all"],
    queryFn: async () =>
      (await api.get("/clients", { params: { page: 1, page_size: 100 } })).data,
  });
}

export function useClientLookup() {
  const { data } = useClientsList();
  const byId = new Map<string, Client>();
  data?.items.forEach((c) => byId.set(c.id, c));
  return byId;
}
