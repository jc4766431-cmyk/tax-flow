"use client";

import { useEffect, useRef, useState } from "react";
import { Send, MessageCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/dashboard/empty-state";
import { useMessageThread } from "@/hooks/use-messages";
import { useCurrentUser } from "@/hooks/use-auth";

export function MessageThread({
  clientId,
  recipientId,
}: {
  clientId: string | null | undefined;
  recipientId: string | null | undefined;
}) {
  const { data: me } = useCurrentUser();
  const { data, isLoading, sendMessage, markRead } = useMessageThread(clientId);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "nearest" });
  }, [data?.items.length]);

  useEffect(() => {
    if (!me || !data) return;
    for (const m of data.items) {
      if (!m.read_at && m.recipient_id === me.id) markRead(m.id);
    }
    // Only re-run when the thread data changes, not on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, me?.id]);

  async function handleSend() {
    const body = draft.trim();
    if (!body || !recipientId) return;
    setSending(true);
    try {
      await sendMessage(recipientId, body);
      setDraft("");
    } finally {
      setSending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Messages</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-10 w-2/3" />
            <Skeleton className="h-10 w-1/2 ml-auto" />
          </div>
        ) : !data || data.items.length === 0 ? (
          <EmptyState
            icon={MessageCircle}
            title="No messages yet"
            description="Send a message to start the conversation."
          />
        ) : (
          <div className="max-h-80 space-y-3 overflow-y-auto pr-1">
            {data.items.map((m) => {
              const mine = m.sender_id === me?.id;
              return (
                <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[75%] rounded-[var(--radius-sm)] border px-3 py-2 text-sm ${
                      mine
                        ? "border-[var(--brass)]/30 bg-[var(--brass)]/10 text-[var(--ink)]"
                        : "border-[var(--line)] bg-[var(--surface-hover)] text-[var(--ink)]"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{m.body}</p>
                    <p className="tabular mt-1 text-right text-[10px] text-[var(--ink-muted)]">
                      {new Date(m.created_at).toLocaleString("en-IN", {
                        hour: "2-digit",
                        minute: "2-digit",
                        day: "2-digit",
                        month: "short",
                      })}
                    </p>
                  </div>
                </div>
              );
            })}
            <div ref={bottomRef} />
          </div>
        )}

        <div className="mt-4 flex items-end gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Write a message…"
            rows={2}
            disabled={!recipientId}
            className="flex-1 resize-none rounded-[var(--radius-sm)] border border-[var(--line-strong)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink)] placeholder:text-[var(--ink-faint)] focus:outline-none focus:ring-1 focus:ring-[var(--brass)]"
          />
          <Button
            type="button"
            onClick={handleSend}
            disabled={!draft.trim() || sending || !recipientId}
          >
            <Send size={16} />
          </Button>
        </div>
        {!recipientId && (
          <p className="mt-2 text-xs text-[var(--ink-muted)]">
            No accountant assigned yet — messaging will open up once one is.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
