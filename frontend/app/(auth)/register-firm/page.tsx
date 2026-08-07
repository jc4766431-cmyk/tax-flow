"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AxiosError } from "axios";
import { AuthCard } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";

const registerFirmSchema = z
  .object({
    firm_name: z.string().min(1, "Enter your firm's name"),
    full_name: z.string().min(2, "Enter your full name"),
    email: z.string().min(1, "Email is required").email("Enter a valid email"),
    password: z.string().min(8, "At least 8 characters"),
    confirm_password: z.string().min(1, "Confirm your password"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

type RegisterFirmValues = z.infer<typeof registerFirmSchema>;

export default function RegisterFirmPage() {
  const { registerFirm } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFirmValues>({ resolver: zodResolver(registerFirmSchema) });

  async function onSubmit(values: RegisterFirmValues) {
    setServerError(null);
    try {
      await registerFirm({
        firm_name: values.firm_name,
        email: values.email,
        password: values.password,
        full_name: values.full_name,
      });
    } catch (err) {
      const message =
        err instanceof AxiosError
          ? err.response?.data?.detail ?? "Could not create your firm's workspace."
          : "Something went wrong. Please try again.";
      setServerError(typeof message === "string" ? message : "Could not create your firm's workspace.");
    }
  }

  return (
    <AuthCard
      title="Set up your firm"
      subtitle="Create your firm's TaxFlow workspace and admin account."
      footer={
        <>
          Already have a firm on TaxFlow?{" "}
          <Link href="/login" className="font-medium text-[var(--brass)] hover:text-[var(--brass-hover)]">
            Sign in
          </Link>
          <br />
          Signing up as a client instead?{" "}
          <Link href="/register" className="font-medium text-[var(--brass)] hover:text-[var(--brass-hover)]">
            Create a client account
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {serverError && (
          <div className="rounded-[var(--radius-sm)] border border-[var(--overdue)]/40 bg-[var(--overdue-bg)] px-3 py-2 text-sm text-[var(--overdue)]">
            {serverError}
          </div>
        )}
        <div>
          <Label htmlFor="firm_name">Firm name</Label>
          <Input id="firm_name" autoComplete="organization" {...register("firm_name")} />
          {errors.firm_name && (
            <p className="mt-1 text-xs text-[var(--overdue)]">{errors.firm_name.message}</p>
          )}
        </div>
        <div>
          <Label htmlFor="full_name">Your full name</Label>
          <Input id="full_name" autoComplete="name" {...register("full_name")} />
          {errors.full_name && (
            <p className="mt-1 text-xs text-[var(--overdue)]">{errors.full_name.message}</p>
          )}
        </div>
        <div>
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" {...register("email")} />
          {errors.email && (
            <p className="mt-1 text-xs text-[var(--overdue)]">{errors.email.message}</p>
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
        <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Creating workspace…" : "Create firm workspace"}
        </Button>
      </form>
    </AuthCard>
  );
}
