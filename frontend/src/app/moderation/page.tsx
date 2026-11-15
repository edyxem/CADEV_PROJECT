"use client";

import Link from "next/link";
import { useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Button } from "@/components/ui/Button";
import { Alert, EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { Input, Select } from "@/components/ui/Field";
import { Badge, Card, PageTitle, Pagination } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { ModerationReport, Paginated } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDate, label, MODERATION_ACTIONS, REPORT_REASONS } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

const ACCOUNT_ONLY = new Set(["PROFILE"]);

function ReportCard({ report, onDone }: { report: ModerationReport; onDone: () => void }) {
  const actions = Object.entries(MODERATION_ACTIONS)
    .filter(([value]) => !(ACCOUNT_ONLY.has(report.target_type) && (value === "HIDE" || value === "DELETE")))
    .map(([value, text]) => ({ value, label: text }));
  const [action, setAction] = useState("NO_ACTION");
  const [reason, setReason] = useState("");
  const [days, setDays] = useState("7");
  const [error, setError] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);

  async function submit() {
    setPending(true);
    setError(null);
    try {
      await api(`/moderation/reports/${report.id}/action/`, {
        method: "POST",
        body: { action, reason, duration_days: action === "SUSPEND" ? Number(days) : null },
      });
      onDone();
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="danger">{label(REPORT_REASONS, report.reason)}</Badge>
        <Badge>{report.target_type}</Badge>
        {report.open_reports_on_target > 1 && <Badge tone="accent">{report.open_reports_on_target} signalements sur cette cible</Badge>}
        <span className="ml-auto text-xs text-muted">{formatDate(report.created_at)} · par {report.reporter}</span>
      </div>
      {report.target ? (
        <div className="mt-3 rounded-lg bg-stone-50 p-3 text-sm">
          <p className="font-medium">
            {report.target.url ? <Link href={report.target.url} className="underline">{report.target.title}</Link> : report.target.title}
          </p>
          {report.target.excerpt && <p className="mt-1 text-muted">{report.target.excerpt}</p>}
          <p className="mt-1 text-xs text-muted">Statut actuel : {report.target.status}{report.target_author ? ` · auteur : ${report.target_author.username}` : ""}</p>
        </div>
      ) : (
        <p className="mt-3 text-sm text-muted">Cible introuvable.</p>
      )}
      {report.details && <p className="mt-2 text-sm">« {report.details} »</p>}

      {report.can_handle ? (
        <div className="mt-4 border-t border-line pt-3">
          {error && <Alert kind="error">{error.code === "validation_error" ? "Vérifiez le motif et la durée." : error.message}</Alert>}
          <div className="grid gap-x-3 sm:grid-cols-2">
            <Select label="Décision" options={actions} value={action} onChange={(e) => setAction(e.target.value)} />
            {action === "SUSPEND" && <Input label="Durée (jours)" type="number" min={1} max={90} value={days} onChange={(e) => setDays(e.target.value)} error={error?.field("duration_days")} />}
          </div>
          <Input label="Motif (journalisé et communiqué au membre)" value={reason} onChange={(e) => setReason(e.target.value)} error={error?.field("reason")} />
          <Button type="button" loading={pending} disabled={reason.trim().length < 5} onClick={submit}>Appliquer la décision</Button>
        </div>
      ) : (
        <p className="mt-3 text-xs text-muted">Vous ne pouvez pas traiter ce signalement (vous en êtes l'auteur ou la cible).</p>
      )}
    </Card>
  );
}

function ModerationContent() {
  const { isModerator } = useAuth();
  const [page, setPage] = useState(1);
  const queue = useApi<Paginated<ModerationReport>>(isModerator ? "/moderation/reports/" : null, { page });

  if (!isModerator) return <EmptyState title="Accès réservé">Cette page est réservée à la modération.</EmptyState>;

  return (
    <div className="mx-auto max-w-3xl">
      <PageTitle title="File de modération" subtitle="Signalements ouverts, du plus ancien au plus récent. Toute décision est journalisée." />
      {queue.loading && !queue.data && <Loading />}
      {queue.error && <ErrorState error={queue.error} onRetry={queue.reload} />}
      {queue.data?.count === 0 && <EmptyState title="File vide">Aucun signalement en attente.</EmptyState>}
      <div className="space-y-3">
        {queue.data?.results.map((report) => <ReportCard key={report.id} report={report} onDone={queue.reload} />)}
      </div>
      {queue.data && <Pagination page={page} count={queue.data.count} onChange={setPage} />}
    </div>
  );
}

export default function ModerationPage() {
  return (
    <RequireAuth>
      <ModerationContent />
    </RequireAuth>
  );
}
