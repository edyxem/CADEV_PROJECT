"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { useEffect } from "react";

import { Loading } from "@/components/ui/Feedback";
import { Avatar } from "@/components/ui/Misc";
import type { Conversation, Paginated } from "@/lib/api/types";
import { useApi } from "@/lib/useApi";

/** Pas de temps réel côté API : la liste est rafraîchie périodiquement. */
export const POLL_MS = 15_000;

const timeFormatter = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

export function ConversationList({ activeId }: { activeId?: string }) {
  const list = useApi<Paginated<Conversation>>("/conversations/", { page_size: 50 });
  const { reload } = list;

  useEffect(() => {
    const timer = window.setInterval(reload, POLL_MS);
    return () => window.clearInterval(timer);
  }, [reload]);

  return (
    <aside className="rounded-2xl border border-line bg-panel p-2" aria-label="Conversations">
      <Link href="/messages" className="mb-1 block rounded-xl px-3 py-2 text-sm font-semibold text-brand-300 hover:bg-ink/5">
        + Nouvelle conversation
      </Link>
      {list.loading && !list.data && <Loading rows={2} />}
      {list.data?.count === 0 && <p className="px-3 py-4 text-sm text-muted">Aucune conversation pour l&apos;instant.</p>}
      <ul className="space-y-1">
        {list.data?.results.map((conversation) => {
          const active = conversation.id === activeId;
          return (
            <li key={conversation.id}>
              <Link
                href={`/messages/${conversation.id}`}
                aria-current={active ? "page" : undefined}
                className={`relative flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors ${active ? "text-ink" : "hover:bg-ink/5"}`}
              >
                {active && <motion.span layoutId="conversation-active" className="absolute inset-0 -z-10 rounded-xl bg-panel-2" transition={{ type: "spring", stiffness: 380, damping: 32 }} />}
                <Avatar author={conversation.other} size={38} />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <span className={`truncate text-sm ${conversation.unread_count > 0 ? "font-bold" : "font-medium"}`}>{conversation.other.display_name}</span>
                    {conversation.last_message_at && <span className="shrink-0 text-[11px] text-muted">{timeFormatter.format(new Date(conversation.last_message_at))}</span>}
                  </span>
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs text-muted">{conversation.last_message?.is_hidden ? "Message masqué" : conversation.last_message?.content}</span>
                    {conversation.unread_count > 0 && (
                      <span className="grid min-w-5 shrink-0 place-items-center rounded-full bg-ocre-500 px-1 text-[11px] font-bold text-night">{conversation.unread_count}</span>
                    )}
                  </span>
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
