"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { SpotlightCard } from "@/components/motion/Interactive";
import { Stagger, StaggerItem } from "@/components/motion/Reveal";
import { Button } from "@/components/ui/Button";
import { Alert, EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { Textarea } from "@/components/ui/Field";
import { Avatar, Badge, Card, PageTitle } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { Mentor, MentorshipRequest, Paginated } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDate, label, MENTORSHIP_STATUS } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

const LANGUAGES: Record<string, string> = { fr: "Français", en: "Anglais", pt: "Portugais", ar: "Arabe", sw: "Swahili", wo: "Wolof", ln: "Lingala" };

function RequestForm({ mentor, onDone }: { mentor: Mentor; onDone: () => void }) {
  const [goal, setGoal] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api("/mentorship-requests/", { method: "POST", body: { mentor: mentor.user.username, goal } });
      onDone();
    } catch (caught) {
      setError(caught as ApiError);
      setSubmitting(false);
    }
  }

  return (
    <motion.form onSubmit={submit} initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="relative z-10 mt-4 overflow-hidden">
      {error && error.code !== "validation_error" && <Alert kind="error">{error.message}</Alert>}
      <Textarea label="Votre objectif" value={goal} onChange={(e) => setGoal(e.target.value)} error={error?.field("goal") ?? error?.field("mentor")} rows={3} hint={`Ce que vous voulez apprendre et votre niveau actuel (30 caractères minimum, ${goal.trim().length}/30).`} />
      <Button type="submit" loading={submitting} disabled={goal.trim().length < 30} className="w-full">
        Envoyer la demande
      </Button>
    </motion.form>
  );
}

function MentorCard({ mentor, canRequest, onRequested }: { mentor: Mentor; canRequest: boolean; onRequested: () => void }) {
  const [open, setOpen] = useState(false);
  const full = mentor.active_mentees >= mentor.max_active_mentees;
  return (
    <SpotlightCard className="h-full p-5">
      <div className="flex items-center gap-3">
        <Avatar author={mentor.user} size={48} />
        <div className="min-w-0">
          <Link href={`/membres/${mentor.user.username}`} className="relative z-10 font-display text-lg font-semibold hover:text-brand-200">
            {mentor.user.display_name}
          </Link>
          <p className="text-sm text-muted">{mentor.headline}</p>
        </div>
      </div>
      {mentor.bio && <p className="mt-3 line-clamp-3 text-sm text-muted">{mentor.bio}</p>}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {mentor.domains.map((domain) => (
          <Badge key={domain.id} tone="accent">{domain.name}</Badge>
        ))}
        {mentor.technologies.map((technology) => (
          <Badge key={technology.id}>{technology.name}</Badge>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted">
        {mentor.languages.map((code) => LANGUAGES[code] ?? code).join(", ")} · {mentor.active_mentees}/{mentor.max_active_mentees} mentoré(s)
      </p>
      {canRequest && (
        <div className="relative z-10 mt-4">
          {full ? (
            <p className="text-sm text-ocre-300">Ce mentor n&apos;a plus de place pour le moment.</p>
          ) : (
            <Button variant={open ? "ghost" : "secondary"} onClick={() => setOpen((value) => !value)} className="w-full">
              {open ? "Annuler" : "Demander un accompagnement"}
            </Button>
          )}
        </div>
      )}
      <AnimatePresence>
        {open && (
          <RequestForm
            mentor={mentor}
            onDone={() => {
              setOpen(false);
              onRequested();
            }}
          />
        )}
      </AnimatePresence>
    </SpotlightCard>
  );
}

function RequestRow({ request, asMentor, onChange }: { request: MentorshipRequest; asMentor: boolean; onChange: () => void }) {
  const [error, setError] = useState("");
  const other = asMentor ? request.mentee : request.mentor;

  async function act(action: string, body?: Record<string, unknown>) {
    setError("");
    try {
      await api(`/mentorship-requests/${request.id}/${action}/`, { method: "POST", body });
      onChange();
    } catch (caught) {
      setError((caught as Error).message);
    }
  }

  const tone: "brand" | "accent" | "neutral" = request.status === "ACCEPTED" ? "brand" : request.status === "PENDING" ? "accent" : "neutral";
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <Avatar author={other} size={36} />
          <div>
            <p className="font-semibold">{other.display_name}</p>
            <p className="text-xs text-muted">{asMentor ? "vous demande un accompagnement" : "votre mentor"} · {formatDate(request.created_at)}</p>
          </div>
        </div>
        <Badge tone={tone}>{label(MENTORSHIP_STATUS, request.status)}</Badge>
      </div>
      <p className="mt-3 text-sm">{request.goal}</p>
      {request.response_message && <p className="mt-2 rounded-xl bg-white/[0.03] px-3 py-2 text-sm text-muted">« {request.response_message} »</p>}
      {error && <p className="mt-2 text-sm text-rose-300">{error}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        {asMentor && request.status === "PENDING" && (
          <>
            <Button onClick={() => act("respond", { accept: true })} className="px-3 py-1.5 text-xs">Accepter</Button>
            <Button variant="secondary" onClick={() => act("respond", { accept: false })} className="px-3 py-1.5 text-xs">Décliner</Button>
          </>
        )}
        {!asMentor && request.status === "PENDING" && (
          <Button variant="secondary" onClick={() => act("cancel")} className="px-3 py-1.5 text-xs">Annuler la demande</Button>
        )}
        {request.status === "ACCEPTED" && (
          <>
            <Link href={`/messages?to=${other.username}`} className="rounded-xl border border-line px-3 py-1.5 text-xs hover:bg-white/5">Écrire un message</Link>
            <Button variant="secondary" onClick={() => act("complete")} className="px-3 py-1.5 text-xs">Marquer comme terminé</Button>
          </>
        )}
      </div>
    </Card>
  );
}

export default function MentorshipPage() {
  const { status, user } = useAuth();
  const authenticated = status === "authenticated";
  const mentors = useApi<Paginated<Mentor>>("/mentors/");
  const asMentee = useApi<Paginated<MentorshipRequest>>(authenticated ? "/mentorship-requests/" : null, { role: "mentee" });
  const asMentor = useApi<Paginated<MentorshipRequest>>(authenticated ? "/mentorship-requests/" : null, { role: "mentor" });
  const [notice, setNotice] = useState(false);

  function refresh() {
    mentors.reload();
    asMentee.reload();
    asMentor.reload();
  }

  return (
    <div>
      <PageTitle eyebrow="Mentorat" title="Apprendre auprès des meilleurs" subtitle="Des développeurs confirmés accompagnent bénévolement les membres de la communauté : orientation, revue de code, préparation aux entretiens." />
      {notice && <Alert kind="success">Demande envoyée ! Le mentor est notifié et vous répondra ici.</Alert>}

      {authenticated && (asMentor.data?.count ?? 0) > 0 && (
        <section className="mb-10">
          <h2 className="mb-3 font-display text-xl font-semibold">Demandes reçues</h2>
          <div className="space-y-3">
            {asMentor.data?.results.map((request) => <RequestRow key={request.id} request={request} asMentor onChange={refresh} />)}
          </div>
        </section>
      )}

      {authenticated && (asMentee.data?.count ?? 0) > 0 && (
        <section className="mb-10">
          <h2 className="mb-3 font-display text-xl font-semibold">Mes demandes</h2>
          <div className="space-y-3">
            {asMentee.data?.results.map((request) => <RequestRow key={request.id} request={request} asMentor={false} onChange={refresh} />)}
          </div>
        </section>
      )}

      <h2 className="mb-3 font-display text-xl font-semibold">Mentors disponibles</h2>
      {!authenticated && (
        <p className="mb-4 text-sm text-muted">
          <Link href="/connexion?next=/mentorat" className="text-brand-300 underline">Connectez-vous</Link> pour demander un accompagnement.
        </p>
      )}
      {mentors.loading && !mentors.data && <Loading />}
      {mentors.error && <ErrorState error={mentors.error} onRetry={mentors.reload} />}
      {mentors.data?.count === 0 && <EmptyState title="Aucun mentor disponible pour le moment" />}
      <Stagger key={mentors.data?.count ?? 0} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {mentors.data?.results.map((mentor) => (
          <StaggerItem key={mentor.id}>
            <MentorCard
              mentor={mentor}
              canRequest={authenticated && mentor.user.username !== user?.username}
              onRequested={() => {
                setNotice(true);
                refresh();
              }}
            />
          </StaggerItem>
        ))}
      </Stagger>
    </div>
  );
}
