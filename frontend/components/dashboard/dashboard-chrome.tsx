"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { NotificationBell } from "@/components/dashboard/notification-bell";
import type { User } from "@/lib/types";

const CLIENT_NAV = [
  { href: "/dashboard", label: "Overview" },
  { href: "/settings", label: "Settings" },
];

const STAFF_NAV = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/clients", label: "Clients" },
  { href: "/admin/board", label: "Workflow Board" },
  { href: "/admin/documents", label: "Document Review" },
  { href: "/admin/invoices", label: "Invoices" },
  { href: "/admin/calendar", label: "Calendar" },
  { href: "/admin/whatsapp", label: "WhatsApp" },
  { href: "/admin/reports", label: "Reports" },
  { href: "/settings", label: "Settings" },
];

export function DashboardChrome({
  user,
  children,
}: {
  user: User;
  children: React.ReactNode;
}) {
  const { logout } = useAuth();
  const pathname = usePathname();
  const isStaff = user.role !== "client";
  const nav = isStaff ? STAFF_NAV : CLIENT_NAV;

  return (
    <div className="min-h-screen bg-[var(--bg)]">
      <header className="sticky top-0 z-40 border-b border-[var(--line)] bg-[var(--bg)]/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-8">
            <Link
              href={isStaff ? "/admin" : "/dashboard"}
              className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-[var(--ink)]"
            >
              TaxFlow<span className="text-[var(--brass)]">.</span>
            </Link>
            <nav className="hidden items-center gap-6 text-sm md:flex">
              {nav.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "text-[var(--ink-muted)] transition-colors hover:text-[var(--ink)]",
                    pathname === item.href && "text-[var(--ink)]"
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <NotificationBell />
            <span className="hidden text-sm text-[var(--ink-muted)] sm:inline">
              {user.full_name}
            </span>
            <button
              onClick={logout}
              className="flex items-center gap-1.5 rounded-[var(--radius-sm)] px-2.5 py-1.5 text-sm text-[var(--ink-muted)] transition-colors hover:bg-[var(--surface)] hover:text-[var(--ink)]"
            >
              <LogOut size={16} />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
