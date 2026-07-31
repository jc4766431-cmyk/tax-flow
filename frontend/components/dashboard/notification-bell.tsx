"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";
import { useNotifications } from "@/hooks/use-notifications";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { data, unreadCount, markRead, markAllRead } = useNotifications();

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
        className="relative flex items-center justify-center rounded-[var(--radius-sm)] p-2 text-[var(--ink-muted)] transition-colors hover:bg-[var(--surface)] hover:text-[var(--ink)]"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--brass)] px-1 text-[10px] font-medium text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-[var(--radius-sm)] border border-[var(--line)] bg-[var(--bg)] shadow-lg">
          <div className="flex items-center justify-between border-b border-[var(--line)] px-4 py-2.5">
            <span className="text-sm font-medium text-[var(--ink)]">Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllRead()}
                className="text-xs text-[var(--ink-muted)] hover:text-[var(--ink)]"
              >
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto">
            {!data || data.items.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-[var(--ink-muted)]">
                No notifications yet.
              </p>
            ) : (
              data.items.map((n) => {
                const content = (
                  <div
                    className={cn(
                      "border-b border-[var(--line)] px-4 py-3 text-sm last:border-b-0",
                      !n.is_read && "bg-[var(--surface)]"
                    )}
                  >
                    <p className="font-medium text-[var(--ink)]">{n.title}</p>
                    {n.body && (
                      <p className="mt-0.5 line-clamp-2 text-[var(--ink-muted)]">{n.body}</p>
                    )}
                  </div>
                );
                return (
                  <button
                    key={n.id}
                    onClick={() => !n.is_read && markRead(n.id)}
                    className="block w-full text-left transition-colors hover:bg-[var(--surface)]"
                  >
                    {n.link_url ? (
                      <Link href={n.link_url}>{content}</Link>
                    ) : (
                      content
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
