"use client";

import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, tokenStorage } from "@/lib/api";
import type { User } from "@/lib/types";

export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ["me"],
    queryFn: async () => (await api.get("/auth/me")).data,
    enabled: typeof window !== "undefined" && !!tokenStorage.getAccess(),
    retry: false,
  });
}

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();

  async function login(email: string, password: string) {
    const { data } = await api.post("/auth/login", { email, password });
    tokenStorage.set(data.access_token, data.refresh_token);
    const { data: user } = await api.get<User>("/auth/me");
    queryClient.setQueryData(["me"], user);
    toast.success(`Welcome back, ${user.full_name.split(" ")[0]}`);
    router.push(user.role === "client" ? "/dashboard" : "/admin");
  }

  async function register(payload: {
    email: string;
    password: string;
    full_name: string;
  }) {
    await api.post("/auth/register", payload);
    toast.success("Account created. Please sign in.");
    router.push("/login");
  }

  async function registerFirm(payload: {
    firm_name: string;
    email: string;
    password: string;
    full_name: string;
  }) {
    const { data } = await api.post("/auth/register-firm", payload);
    toast.success(`${data.firm.name} is set up. Please sign in.`);
    router.push("/login");
  }

  async function acceptInvite(payload: {
    token: string;
    full_name: string;
    password: string;
  }) {
    await api.post("/auth/accept-invite", payload);
    toast.success("Account created. Please sign in.");
    router.push("/login");
  }

  function logout() {
    tokenStorage.clear();
    queryClient.clear();
    router.push("/login");
  }

  return { login, register, registerFirm, acceptInvite, logout };
}
