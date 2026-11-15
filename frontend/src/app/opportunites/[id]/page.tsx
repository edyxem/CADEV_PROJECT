"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ReportButton } from "@/components/community/Actions";
import { Reveal } from "@/components/motion/Reveal";
import { daysLeft } from "@/components/opportunities/OpportunityCard";
import { Button } from "@/components/ui/Button";
import { Alert, ErrorState, Loading } from "@/components/ui/Feedback";
import { Select, Textarea } from "@/components/ui/Field";
import { AuthorLine, Badge, Card, RichText } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { Opportunity } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDay, label, LEVELS, OPPORTUNITY_TYPES, WORK_MODES } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

function InterestForm({ opportunityId }: { opportunityId: string }) {
  const [kind, setKind] = useState("APPLICATION");
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api(`/opportunities/${opportunityId}/interests/`, { method: "POST", body: { kind, message } });
      setSent(true);
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setSubmitting(false);
    }
  }

  if (sent) return <Alert kind="success">Votre demande a été transmise à l&apos;auteur de l&apos;annonce, qui est notifié.</Alert>;
  return (
    <form onSubmit={submit}>
      {error && error.code !== "validation_error" && <Alert kind="error">{error.message}</Alert>}
      <Select
        label="Je souhaite"
        options={[
          { value: "APPLICATION", label: "Candidater" },
          { value: "INFORMATION", label: "Demander des informations" },
        ]}
        value={kind}
        onChange={(e) => setKind(e.target.value)}
      />
      <Textarea label="Message" value={message} onChange={(e) => setMessage(e.target.value)} error={error?.field("message")} rows={4} hint="Présentez-vous en quelques lignes : expérience, motivation, disponibilité." />
      <Button type="submit" loading={submitting} className="w-full">
        Envoyer
      </Button>
    </form>
  );
}

export default function OpportunityPage() {
  const { id } = useParams<{ id: string }>();
  const { status, user } = useAuth();
  const result = useApi<Opportunity>(`/opportunities/${id}/`);

  if (result.loading && !result.data) return <Loading />;
  if (result.error) return <ErrorState error={result.error} onRetry={result.reload} />;
  const opportunity = result.data;
  if (!opportunity) return null;
  const remaining = daysLeft(opportunity.deadline);
  const isPublisher = user?.username === opportunity.publisher.username;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
      <Reveal>
        <Link href="/opportunites" className="text-sm text-muted hover:text-ink">
          ← Toutes les opportunités
        </Link>
        <div className="mb-3 mt-4 flex flex-wrap gap-2">
          <Badge tone="accent">{label(OPPORTUNITY_TYPES, opportunity.type)}</Badge>
          <Badge>{label(WORK_MODES, opportunity.work_mode)}</Badge>
          {opportunity.level && <Badge>{label(LEVELS, opportunity.level)}</Badge>}
          {opportunity.is_verified_partner && <Badge tone="brand">✓ Partenaire vérifié</Badge>}
          {opportunity.is_expired && <Badge tone="danger">Expirée</Badge>}
        </div>
        <h1 className="font-display text-3xl font-bold leading-tight sm:text-4xl">{opportunity.title}</h1>
        <p className="mt-2 text-muted">
          {opportunity.organization_label}
          {opportunity.country ? ` · ${opportunity.country.name}` : ""}
          {opportunity.location ? ` · ${opportunity.location}` : ""}
        </p>
        <div className="mt-4">
          <AuthorLine author={opportunity.publisher}>
            <span>· publiée le {formatDay(opportunity.published_at)}</span>
          </AuthorLine>
        </div>
        <Card className="mt-6">
          <RichText html={opportunity.description} />
          {opportunity.technologies.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {opportunity.technologies.map((technology) => (
                <span key={technology.id} className="rounded-md bg-white/[0.04] px-2 py-0.5 font-mono text-xs text-muted">
                  {technology.name}
                </span>
              ))}
            </div>
          )}
        </Card>
        <div className="mt-4">
          <ReportButton targetType="OPPORTUNITY" targetId={opportunity.id} />
        </div>
      </Reveal>

      <Reveal delay={0.1}>
        <div className="space-y-4 lg:sticky lg:top-28">
          {opportunity.deadline && (
            <Card>
              <p className="text-xs uppercase tracking-wider text-muted">Date limite</p>
              <p className="mt-1 font-display text-2xl font-bold">{formatDay(opportunity.deadline)}</p>
              {remaining !== null && remaining >= 0 && <p className="mt-1 text-sm text-ocre-300">Plus que {remaining} jour(s)</p>}
            </Card>
          )}
          {(opportunity.application_url || opportunity.contact_email || opportunity.source_url) && (
            <Card className="space-y-2 text-sm">
              {opportunity.application_url && (
                <a href={opportunity.application_url} target="_blank" rel="noopener noreferrer" className="btn-primary block rounded-xl px-4 py-2.5 text-center">
                  Postuler sur le site ↗
                </a>
              )}
              {opportunity.contact_email && (
                <p>
                  Contact : <a href={`mailto:${opportunity.contact_email}`} className="text-brand-300 underline">{opportunity.contact_email}</a>
                </p>
              )}
              {opportunity.source_url && (
                <p>
                  <a href={opportunity.source_url} target="_blank" rel="noopener noreferrer" className="text-muted underline">
                    Source de l&apos;annonce ↗
                  </a>
                </p>
              )}
            </Card>
          )}
          {!opportunity.is_expired && !isPublisher && (
            <Card>
              <h2 className="mb-3 font-display text-lg font-semibold">Manifester mon intérêt</h2>
              {status === "authenticated" ? (
                <InterestForm opportunityId={opportunity.id} />
              ) : (
                <p className="text-sm text-muted">
                  <Link href={`/connexion?next=/opportunites/${opportunity.id}`} className="text-brand-300 underline">
                    Connectez-vous
                  </Link>{" "}
                  pour candidater ou poser une question.
                </p>
              )}
            </Card>
          )}
        </div>
      </Reveal>
    </div>
  );
}
