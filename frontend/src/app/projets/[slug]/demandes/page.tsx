"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Button } from "@/components/ui/Button";
import { Alert, EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { AuthorLine, Badge, Card, PageTitle } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { JoinRequest, Paginated } from "@/lib/api/types";
import { formatDate } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

const STATUS: Record<string, string> = { PENDING: "En attente", ACCEPTED: "Acceptée", REJECTED: "Refusée", WITHDRAWN: "Retirée" };

function RequestsContent() {
  const { slug } = useParams<{ slug: string }>();
  const [filter, setFilter] = useState("PENDING");
  const requests = useApi<Paginated<JoinRequest>>(`/projects/${slug}/join-requests/`, { status: filter || undefined, page_size: 100 });
  const [roles, setRoles] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function decide(request: JoinRequest, decision: "accept" | "reject") {
    setError(null);
    try {
      await api(`/join-requests/${request.id}/${decision}/`, {
        method: "POST",
        body: decision === "accept" ? { role: roles[request.id] ?? "CONTRIBUTOR" } : {},
      });
      requests.reload();
    } catch (caught) {
      setError((caught as ApiError).message);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageTitle title="Demandes pour rejoindre" subtitle="Visibles uniquement du propriétaire et des responsables habilités." action={<Link href={`/projets/${slug}`} className="text-sm text-brand-300 underline">Retour au projet</Link>} />
      <div className="mb-4 flex gap-2 text-sm">
        {[["PENDING", "En attente"], ["", "Toutes"]].map(([value, text]) => (
          <button key={value} type="button" onClick={() => setFilter(value)} aria-pressed={filter === value} className="rounded-full border border-line px-3 py-1 aria-pressed:border-brand-400/60 aria-pressed:bg-brand-50">
            {text}
          </button>
        ))}
      </div>
      {error && <Alert kind="error">{error}</Alert>}
      {requests.loading && !requests.data && <Loading />}
      {requests.error && <ErrorState error={requests.error} onRetry={requests.reload} />}
      {requests.data?.count === 0 && <EmptyState title="Aucune demande">Les nouvelles candidatures apparaîtront ici.</EmptyState>}
      <div className="space-y-3">
        {requests.data?.results.map((request) => (
          <Card key={request.id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <AuthorLine author={request.user}><span>· {formatDate(request.created_at)}</span></AuthorLine>
              <Badge tone={request.status === "PENDING" ? "accent" : "neutral"}>{STATUS[request.status]}</Badge>
            </div>
            {request.requested_role && <p className="mt-2 text-sm">Rôle visé : <span className="font-medium">{request.requested_role.role_name}</span></p>}
            <p className="mt-2 whitespace-pre-line text-sm">{request.message}</p>
            {request.status === "PENDING" && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <label className="text-sm">
                  <span className="sr-only">Rôle attribué</span>
                  <select className="rounded-xl border border-line px-2 py-2 text-sm" value={roles[request.id] ?? "CONTRIBUTOR"} onChange={(e) => setRoles({ ...roles, [request.id]: e.target.value })}>
                    <option value="CONTRIBUTOR">Contributeur</option>
                    <option value="OBSERVER">Observateur</option>
                    <option value="MANAGER">Responsable</option>
                  </select>
                </label>
                <Button type="button" onClick={() => decide(request, "accept")}>Accepter</Button>
                <Button type="button" variant="secondary" onClick={() => decide(request, "reject")}>Refuser</Button>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

export default function RequestsPage() {
  return (
    <RequireAuth>
      <RequestsContent />
    </RequireAuth>
  );
}
