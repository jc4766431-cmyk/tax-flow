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

// No full_name field here (unlike /accept-invite) — a quick-added client's
// name was already set by staff via POST /clients/quick-add and lives on
// the shadow User already; this form only needs to set a real password
// (required) and, optionally, a real email to replace the unusable
// @taxflow.internal placeholder.
const activateSchema = z
  .object({
    email: z.string().email("Enter a valid email").optional().or(z.literal("")),
    password: z.string().min(8, "At least 8 characters"),
    confirm_password: z.string().min(1, "Confirm your password"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

type ActivateValues = z.infer<typeof activateSchema>;

function AcceptClientInviteForm() {
  const { acceptClientInvite } = useAuth();
  const token = useSearchParams().get("token");
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ActivateValues>({ resolver: zodResolver(activateSchema) });

  async function onSubmit(values: ActivateValues) {
    if (!token) {
      setServerError("This link is missing its token. Ask your accountant to resend it.");
      return;
    }
    setServerError(null);
    try {
      await acceptClientInvite({
        token,
        password: values.password,
        email: values.email || undefined,
      });
    } catch (err) {
      const message =
        err instanceof AxiosError
          ? err.response?.data?.detail ?? "This link is invalid or has expired."
          : "Something went wrong. Please try again.";
      setServerError(typeof message === "string" ? message : "This link is invalid or has expired.");
    }
  }

  return (
    <AuthCard
      title="Set up web portal access"
      subtitle="You've been using WhatsApp with your accountant so far — set a password to also access your filings and documents here."
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
            This link is missing its token. Ask your accountant to send you a new one.
          </div>
        )}
        {serverError && (
          <div className="rounded-[var(--radius-sm)] border border-[var(--overdue)]/40 bg-[var(--overdue-bg)] px-3 py-2 text-sm text-[var(--overdue)]">
            {serverError}
          </div>
        )}
        <div>
          <Label htmlFor="email">Email (optional)</Label>
          <Input id="email" type="email" autoComplete="email" {...register("email")} />
          {errors.email && <p className="mt-1 text-xs text-[var(--overdue)]">{errors.email.message}</p>}
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
          {isSubmitting ? "Setting up…" : "Set up portal access"}
        </Button>
      </form>
    </AuthCard>
  );
}

export default function AcceptClientInvitePage() {
  return (
    <Suspense fallback={null}>
      <AcceptClientInviteForm />
    </Suspense>
  );
}
