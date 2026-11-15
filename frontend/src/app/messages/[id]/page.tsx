"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { ReportButton } from "@/components/community/Actions";
import { RequireAuth } from "@/components/layout/RequireAuth";
import { ConversationList, POLL_MS } from "@/components/messaging/ConversationList";
import { Button } from "@/components/ui/Button";
import { Alert, ErrorState, Loading } from "@/components/ui/Feedback";
import { Avatar } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { Conversation, Message, Paginated } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useApi } from "@/lib/useApi";

const timeFormatter = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" });

function Thread({ id }: { id: string }) {
  const { user } = useAuth();
  const conversation = useApi<Conversation>(`/conversations/${id}/`);
  const messages = useApi<Paginated<Message>>(`/conversations/${id}/messages/`, { page_size: 100 });
  const [sent, setSent] = useState<Message[]>([]);
  const [content, setContent] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [sending, setSending] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const reloadMessages = messages.reload;

  // Rafraîchissement périodique et accusé de lecture.
  useEffect(() => {
    api(`/conversations/${id}/read/`, { method: "POST" }).catch(() => undefined);
    const timer = window.setInterval(() => {
      reloadMessages();
      api(`/conversations/${id}/read/`, { method: "POST" }).catch(() => undefined);
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [id, reloadMessages]);

  const loaded = messages.data?.results ?? [];
  const known = new Set(loaded.map((message) => message.id));
  const ordered = [...loaded].reverse().concat(sent.filter((message) => !known.has(message.id)));
  const count = ordered.length;

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [count]);

  async function send(event?: FormEvent) {
    event?.preventDefault();
    if (!content.trim()) return;
    setSending(true);
    setError(null);
    try {
      const message = await api<Message>(`/conversations/${id}/messages/`, { method: "POST", body: { content } });
      setSent((previous) => [...previous, message]);
      setContent("");
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  }

  async function block() {
    const other = conversation.data?.other.username;
    if (!other || !window.confirm("Bloquer ce membre ? Il ne pourra plus vous écrire.")) return;
    try {
      await api("/blocks/", { method: "POST", body: { username: other } });
      setBlocked(true);
    } catch (caught) {
      setError(caught as ApiError);
    }
  }

  if (conversation.error) return <ErrorState error={conversation.error} />;
  const other = conversation.data?.other;

  return (
    <section className="flex h-[70vh] min-h-[28rem] flex-col rounded-2xl border border-line bg-panel" aria-label="Conversation">
      <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        {other ? (
          <Link href={`/membres/${other.username}`} className="flex items-center gap-3 hover:text-brand-200">
            <Avatar author={other} size={36} />
            <span className="font-semibold">{other.display_name}</span>
          </Link>
        ) : (
          <span className="skeleton h-9 w-40" />
        )}
        <div className="flex items-center gap-3 text-xs">
          <button type="button" onClick={block} className="text-muted hover:text-rose-700">
            Bloquer
          </button>
        </div>
      </header>

      <div className="flex-1 space-y-2 overflow-y-auto px-4 py-4">
        {messages.loading && !messages.data && <Loading rows={2} />}
        <AnimatePresence initial={false}>
          {ordered.map((message) => {
            const mine = message.sender.username === user?.username;
            return (
              <motion.div
                key={message.id}
                layout
                initial={{ opacity: 0, y: 12, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ type: "spring", stiffness: 420, damping: 32 }}
                className={`flex ${mine ? "justify-end" : "justify-start"}`}
              >
                <div className={`group max-w-[80%] rounded-2xl px-3.5 py-2 text-sm ${mine ? "rounded-br-md bg-gradient-to-br from-brand-400 to-brand-600 text-night" : "rounded-bl-md bg-panel-2"}`}>
                  <p className="whitespace-pre-wrap break-words">{message.is_hidden ? <em className="opacity-70">Message masqué par la modération</em> : message.content}</p>
                  <p className={`mt-0.5 text-[10px] ${mine ? "text-night/70" : "text-muted"}`}>{timeFormatter.format(new Date(message.created_at))}</p>
                  {!mine && !message.is_hidden && (
                    <div className="hidden pt-1 group-hover:block">
                      <ReportButton targetType="MESSAGE" targetId={message.id} />
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        <div ref={bottom} />
      </div>

      <div className="border-t border-line p-3">
        {blocked && <Alert kind="info">Membre bloqué. Vous pouvez le débloquer en contactant la modération.</Alert>}
        {error && <Alert kind="error">{error.field("content") ?? error.message}</Alert>}
        <form onSubmit={send} className="flex items-end gap-2">
          <label htmlFor="message-input" className="sr-only">
            Votre message
          </label>
          <textarea
            id="message-input"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="Écrire un message… (Entrée pour envoyer)"
            className="max-h-32 min-h-11 flex-1 resize-none rounded-xl border border-line bg-panel-2 px-3 py-2.5 text-sm focus:border-brand-400/60 focus:outline-none"
          />
          <Button type="submit" loading={sending} disabled={!content.trim() || blocked}>
            Envoyer
          </Button>
        </form>
      </div>
    </section>
  );
}

export default function ConversationPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <RequireAuth>
      <div className="grid gap-4 lg:grid-cols-[20rem_1fr]">
        <div className="hidden lg:block">
          <ConversationList activeId={id} />
        </div>
        <div>
          <Link href="/messages" className="mb-3 inline-block text-sm text-muted hover:text-ink lg:hidden">
            ← Conversations
          </Link>
          <Thread id={id} />
        </div>
      </div>
    </RequireAuth>
  );
}
