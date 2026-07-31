"use client";

import { useState } from "react";
import Link from "next/link";
import { AxiosError } from "axios";
import { toast } from "sonner";
import { ShieldCheck, ShieldOff, KeyRound } from "lucide-react";
import { api } from "@/lib/api";
import { useCurrentUser } from "@/hooks/use-auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

function errorMessage(err: unknown, fallback: string) {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

function TwoFactorSetup({ onEnabled }: { onEnabled: () => void }) {
  const [secret, setSecret] = useState<string | null>(null);
  const [uri, setUri] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  async function startSetup() {
    setBusy(true);
    try {
      const { data } = await api.post("/auth/2fa/setup");
      setSecret(data.secret);
      setUri(data.provisioning_uri);
    } catch (err) {
      toast.error(errorMessage(err, "Couldn't start 2FA setup."));
    } finally {
      setBusy(false);
    }
  }

  async function confirmEnable() {
    if (code.length !== 6) return;
    setBusy(true);
    try {
      await api.post("/auth/2fa/enable", { totp_code: code });
      toast.success("Two-factor authentication enabled");
      onEnabled();
    } catch (err) {
      toast.error(errorMessage(err, "That code didn't verify. Try again."));
    } finally {
      setBusy(false);
    }
  }

  if (!secret) {
    return (
      <Button variant="secondary" size="sm" onClick={startSetup} disabled={busy}>
        {busy ? "Starting…" : "Set up two-factor authentication"}
      </Button>
    );
  }

  return (
    <div className="space-y-3 rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--bg)] p-4">
      <p className="text-sm text-[var(--ink-muted)]">
        Add this account to your authenticator app, then enter the 6-digit code it
        generates to confirm.
      </p>
      <div>
        <Label>Manual entry key</Label>
        <Input readOnly value={secret} className="font-[family-name:var(--font-mono)] text-xs" />
      </div>
      {uri && (
        <p className="break-all text-xs text-[var(--ink-muted)]">{uri}</p>
      )}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <Label htmlFor="totp-confirm">6-digit code</Label>
          <Input
            id="totp-confirm"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          />
        </div>
        <Button onClick={confirmEnable} disabled={busy || code.length !== 6}>
          {busy ? "Verifying…" : "Confirm"}
        </Button>
      </div>
    </div>
  );
}

function TwoFactorDisableForm({ onDisabled }: { onDisabled: () => void }) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    try {
      await api.post("/auth/2fa/disable", { password, totp_code: code });
      toast.success("Two-factor authentication disabled");
      onDisabled();
    } catch (err) {
      toast.error(errorMessage(err, "Couldn't disable 2FA. Check your password and code."));
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        Disable two-factor authentication
      </Button>
    );
  }

  return (
    <div className="space-y-3 rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--bg)] p-4">
      <div>
        <Label htmlFor="disable-password">Password</Label>
        <Input
          id="disable-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      <div>
        <Label htmlFor="disable-code">6-digit code</Label>
        <Input
          id="disable-code"
          inputMode="numeric"
          maxLength={6}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
        />
      </div>
      <div className="flex gap-2">
        <Button
          variant="outline"
          onClick={submit}
          disabled={busy || !password || code.length !== 6}
        >
          {busy ? "Disabling…" : "Confirm disable"}
        </Button>
        <Button variant="ghost" onClick={() => setOpen(false)} disabled={busy}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const { data: user, isLoading, refetch } = useCurrentUser();

  if (isLoading || !user) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-1/4" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">
        Settings
      </h1>

      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label>Full name</Label>
              <Input readOnly value={user.full_name} />
            </div>
            <div>
              <Label>Email</Label>
              <Input readOnly value={user.email} />
            </div>
          </div>
          <div className="flex items-center gap-2 pt-1">
            <Badge>{user.role.replace("_", " ")}</Badge>
            {!user.is_email_verified && (
              <span className="text-xs text-[var(--ink-muted)]">Email not verified</span>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <KeyRound size={18} className="text-[var(--ink-muted)]" />
          <CardTitle>Password</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-sm text-[var(--ink-muted)]">
            Change your password via a reset link sent to your email.
          </p>
          <Link href="/forgot-password">
            <Button variant="secondary" size="sm">
              Send password reset link
            </Button>
          </Link>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          {user.two_factor_enabled ? (
            <ShieldCheck size={18} className="text-[var(--ink-muted)]" />
          ) : (
            <ShieldOff size={18} className="text-[var(--ink-muted)]" />
          )}
          <CardTitle>Two-factor authentication</CardTitle>
        </CardHeader>
        <CardContent>
          {user.two_factor_enabled ? (
            <div className="space-y-3">
              <p className="text-sm text-[var(--ink-muted)]">
                Two-factor authentication is currently enabled on your account.
              </p>
              <TwoFactorDisableForm onDisabled={() => refetch()} />
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-[var(--ink-muted)]">
                Add an extra layer of security by requiring a code from an
                authenticator app at sign-in.
              </p>
              <TwoFactorSetup onEnabled={() => refetch()} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
