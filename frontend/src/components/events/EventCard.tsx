"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/Misc";
import { api } from "@/lib/api/client";
import type { EventItem } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { EVENT_FORMATS, EVENT_KINDS, label } from "@/lib/labels";

const day = new Intl.DateTimeFormat("fr-FR", { day: "2-digit" });
const month = new Intl.DateTimeFormat("fr-FR", { month: "short" });
const time = new Intl.DateTimeFormat("fr-FR", { weekday: "long", hour: "2-digit", minute: "2-digit" });

/** Bouton d'inscription avec mise à jour optimiste du compteur. */
export function RegisterButton({ event, onChange }: { event: EventItem; onChange?: (event: EventItem) => void }) {
  const { status } = useAuth();
  const [current, setCurrent] = useState(event);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const full = current.capacity !== null && current.registered_count >= current.capacity && !current.is_registered;

  if (status !== "authenticated" || current.is_past || current.status === "CANCELLED") return null;

  async function toggle() {
    setBusy(true);
    setError("");
    const next = { ...current, is_registered: !current.is_registered, registered_count: current.registered_count + (current.is_registered ? -1 : 1) };
    try {
      await api(`/events/${current.id}/register/`, { method: current.is_registered ? "DELETE" : "POST" });
      setCurrent(next);
      onChange?.(next);
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative z-10">
      <motion.button
        type="button"
        whileTap={{ scale: 0.95 }}
        disabled={busy || full}
        onClick={toggle}
        className={`rounded-xl px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-50 ${current.is_registered ? "border border-brand-400/50 bg-brand-500/15 text-brand-200" : "btn-primary"}`}
      >
        {current.is_registered ? "✓ Inscrit · se désinscrire" : full ? "Complet" : "S'inscrire"}
      </motion.button>
      {error && <p className="mt-1 text-xs text-rose-300">{error}</p>}
    </div>
  );
}

export function EventCard({ event }: { event: EventItem }) {
  const start = new Date(event.starts_at);
  const cancelled = event.status === "CANCELLED";
  return (
    <motion.article
      whileHover={{ y: -3 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
      className={`group relative flex gap-4 rounded-2xl border border-line bg-panel p-4 transition-colors hover:border-brand-400/35 ${event.is_past || cancelled ? "opacity-70" : ""}`}
    >
      <div className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-brand-500/25 to-ocre-500/20 text-center">
        <div>
          <p className="font-display text-2xl font-bold leading-none">{day.format(start)}</p>
          <p className="text-[11px] uppercase tracking-wider text-ocre-300">{month.format(start)}</p>
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex flex-wrap gap-1.5">
          <Badge tone="accent">{label(EVENT_KINDS, event.kind)}</Badge>
          <Badge>{label(EVENT_FORMATS, event.format)}</Badge>
          {cancelled && <Badge tone="danger">Annulé</Badge>}
        </div>
        <h3 className="font-display text-lg font-semibold leading-snug">
          <Link href={`/evenements/${event.id}`} className="after:absolute after:inset-0 group-hover:text-brand-200">
            {event.title}
          </Link>
        </h3>
        <p className="mt-0.5 text-sm capitalize text-muted">
          {time.format(start)}
          {event.location ? ` · ${event.location}` : ""}
        </p>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-muted">
            {event.registered_count} inscrit(s){event.capacity ? ` / ${event.capacity} places` : ""} · par {event.organizer.display_name}
          </p>
          <RegisterButton event={event} />
        </div>
      </div>
    </motion.article>
  );
}
