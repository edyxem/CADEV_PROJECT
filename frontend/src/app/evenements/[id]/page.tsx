"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { ReportButton } from "@/components/community/Actions";
import { RegisterButton } from "@/components/events/EventCard";
import { Reveal } from "@/components/motion/Reveal";
import { ErrorState, Loading } from "@/components/ui/Feedback";
import { AuthorLine, Badge, Card, RichText } from "@/components/ui/Misc";
import type { EventItem } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { EVENT_FORMATS, EVENT_KINDS, formatDate, label } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

export default function EventPage() {
  const { id } = useParams<{ id: string }>();
  const { status } = useAuth();
  const result = useApi<EventItem>(`/events/${id}/`);

  if (result.loading && !result.data) return <Loading />;
  if (result.error) return <ErrorState error={result.error} onRetry={result.reload} />;
  const event = result.data;
  if (!event) return null;
  const filled = event.capacity ? Math.min(100, Math.round((event.registered_count / event.capacity) * 100)) : null;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
      <Reveal>
        <Link href="/evenements" className="text-sm text-muted hover:text-ink">
          ← Tous les événements
        </Link>
        <div className="mb-3 mt-4 flex flex-wrap gap-2">
          <Badge tone="accent">{label(EVENT_KINDS, event.kind)}</Badge>
          <Badge>{label(EVENT_FORMATS, event.format)}</Badge>
          {event.status === "CANCELLED" && <Badge tone="danger">Annulé</Badge>}
          {event.is_past && <Badge>Terminé</Badge>}
          {event.technologies.map((technology) => (
            <Badge key={technology.id}>{technology.name}</Badge>
          ))}
        </div>
        <h1 className="font-display text-3xl font-bold leading-tight sm:text-4xl">{event.title}</h1>
        <div className="mt-4">
          <AuthorLine author={event.organizer}>
            <span>· organisateur</span>
          </AuthorLine>
        </div>
        <Card className="mt-6">
          <RichText html={event.description} />
        </Card>
        <div className="mt-4">
          <ReportButton targetType="EVENT" targetId={event.id} />
        </div>
      </Reveal>

      <Reveal delay={0.1}>
        <Card className="space-y-4 lg:sticky lg:top-28">
          <div>
            <p className="text-xs uppercase tracking-wider text-muted">Début</p>
            <p className="mt-1 font-semibold">{formatDate(event.starts_at)}</p>
            <p className="mt-2 text-xs uppercase tracking-wider text-muted">Fin</p>
            <p className="mt-1 font-semibold">{formatDate(event.ends_at)}</p>
          </div>
          {event.location && (
            <div>
              <p className="text-xs uppercase tracking-wider text-muted">Lieu</p>
              <p className="mt-1">{event.location}</p>
            </div>
          )}
          {event.online_url && event.is_registered && (
            <a href={event.online_url} target="_blank" rel="noopener noreferrer" className="block text-sm text-brand-300 underline">
              Rejoindre en ligne ↗
            </a>
          )}
          <div>
            <p className="text-sm">
              <span className="font-display text-2xl font-bold">{event.registered_count}</span> inscrit(s)
              {event.capacity ? ` sur ${event.capacity} places` : ""}
            </p>
            {filled !== null && (
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/5">
                <div className="h-full rounded-full bg-gradient-to-r from-brand-400 to-ocre-400 transition-[width] duration-700" style={{ width: `${filled}%` }} />
              </div>
            )}
          </div>
          {status === "authenticated" ? (
            <RegisterButton event={event} onChange={() => result.reload()} />
          ) : (
            !event.is_past && (
              <p className="text-sm text-muted">
                <Link href={`/connexion?next=/evenements/${event.id}`} className="text-brand-300 underline">
                  Connectez-vous
                </Link>{" "}
                pour vous inscrire.
              </p>
            )
          )}
        </Card>
      </Reveal>
    </div>
  );
}
