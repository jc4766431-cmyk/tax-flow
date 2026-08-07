"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AxiosError } from "axios";
import { AuthCard } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";

const acceptInviteSchema = z
  .object({
    full_name: z.string().min(2, "Enter your full name"),
    password: z.string().min(8, "At least 8 characters"),
    confirm_password: z.string().min(1, "Confirm your password"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

type AcceptInviteValues = z.infer<typeof acceptInviteSchema>;

function AcceptInviteForm() {
  const { acceptInvite } = useAuth();
  const token = useSearchParams().get("token");
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AcceptInviteValues>({ resolver: zodResolver(acceptInviteSchema) });

  async function onSubmit(values: AcceptInviteValues) {
    if (!token) {
      setServerError("This invite link is missing its token. Ask your firm admin to resend it.");
      return;
    }
    setServerError(null);
    try {
      await acceptInvite({
        token,
        full_name: values.full_name,
        password: values.password,
      });
    } catch (err) {
      const message =
        err instanceof AxiosError
          ? err.response?.data?.detail ?? "This invite is invalid or has expired."
          : "Something went wrong. Please try again.";
      setServerError(typeof message === "string" ? message : "This invite is invalid or has expired.");
    }
  }

  return (
    <AuthCard
      title="Accept your invite"
      subtitle="Set a password to finish joining your firm's TaxFlow workspace."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-[var(--brass)] hover:text-[var(--brass-hover)]">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {!token && (
          <div className="rounded-[var(--radius-sm)] border border-[var(--overdue)]/40 bg-[var(--overdue-bg)] px-3 py-2 text-sm text-[var(--overdue)]">
            This link is missing its invite token. Ask your firm admin to send you a new invite.
          </div>
        )}
        {serverError && (
          <div className="rounded-[var(--radius-sm)] border border-[var(--overdue)]/40 bg-[var(--overdue-bg)] px-3 py-2 text-sm text-[var(--overdue)]">
            {serverError}
          </div>
        )}
        <div>
          <Label htmlFor="full_name">Full name</Label>
          <Input id="full_name" autoComplete="name" {...register("full_name")} />
          {errors.full_name && (
            <p className="mt-1 text-xs text-[var(--overdue)]">{errors.full_name.message}</p>
          )}
        </div>
        <div>
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="new-password" {...register("password")} />
          {errors.password && (
            <p className="mt-1 text-xs text-[var(--overdue)]">{errors.password.message}</p>
          )}
        </div>
        <div>
          <Label htmlFor="confirm_password">Confirm password</Label>
          <Input
            id="confirm_password"
            type="password"
            autoComplete="new-password"
            {...register("confirm_password")}
          />
          {errors.confirm_password && (
            <p className="mt-1 text-xs text-[var(--overdue)]">{errors.confirm_password.message}</p>
          )}
        </div>
        <Button type="submit" size="lg" className="w-full" disabled={isSubmitting || !token}>
          {isSubmitting ? "Joining…" : "Accept invite"}
        </Button>
      </form>
    </AuthCard>
  );
}

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={null}>
      <AcceptInviteForm />
    </Suspense>
  );
}
