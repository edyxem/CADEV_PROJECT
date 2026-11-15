"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ReportButton } from "@/components/community/Actions";
import { Button } from "@/components/ui/Button";
import { Alert, ErrorState, Loading } from "@/components/ui/Feedback";
import { Input, Select, Textarea } from "@/components/ui/Field";
import { AuthorLine, Badge, Card, RichText } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { JoinRequest, Member, Paginated, ProjectDetail } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { label, PROJECT_ROLES, PROJECT_STATUS, TASK_STATUS } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

// Transitions proposées au propriétaire (le serveur reste seul juge, §11.11).
const NEXT_STATUSES: Record<string, string[]> = {
  IDEA: ["RECRUITING", "IN_PROGRESS", "PAUSED", "ARCHIVED"],
  RECRUITING: ["IN_PROGRESS", "PAUSED", "ARCHIVED"],
  IN_PROGRESS: ["RECRUITING", "PAUSED", "COMPLETED", "ARCHIVED"],
  PAUSED: ["RECRUITING", "IN_PROGRESS", "ARCHIVED"],
  COMPLETED: ["IN_PROGRESS", "ARCHIVED"],
  ARCHIVED: ["PAUSED"],
};

function JoinForm({ project, onSent }: { project: ProjectDetail; onSent: () => void }) {
  const [message, setMessage] = useState("");
  const [role, setRole] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);
  const openRoles = project.role_needs.filter((need) => need.is_open);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await api(`/projects/${project.slug}/join-requests/`, { method: "POST", body: { message, requested_role: role || null } });
      onSent();
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit}>
      {error && error.code !== "validation_error" && <Alert kind="error">{error.message}</Alert>}
      {openRoles.length > 0 && (
        <Select label="Rôle visé" options={[{ value: "", label: "Sans rôle précis" }, ...openRoles.map((need) => ({ value: need.id, label: need.role_name }))]} value={role} onChange={(e) => setRole(e.target.value)} />
      )}
      <Textarea label="Votre motivation" value={message} onChange={(e) => setMessage(e.target.value)} rows={4} hint="20 caractères minimum : compétences, disponibilité, ce que vous souhaitez apporter." error={error?.field("message")} />
      <Button type="submit" loading={pending}>Envoyer ma demande</Button>
    </form>
  );
}

function RoleNeedForm({ slug, onSaved }: { slug: string; onSaved: () => void }) {
  const [form, setForm] = useState({ role_name: "", description: "", slots: "1" });
  const [error, setError] = useState<ApiError | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api(`/projects/${slug}/roles/`, { method: "POST", body: { ...form, slots: Number(form.slots) } });
      setForm({ role_name: "", description: "", slots: "1" });
      onSaved();
    } catch (caught) {
      setError(caught as ApiError);
    }
  }

  return (
    <form onSubmit={submit} className="mt-4 rounded-lg border border-dashed border-line p-3">
      <p className="mb-2 text-sm font-medium">Ajouter un rôle recherché</p>
      <div className="grid gap-x-3 sm:grid-cols-[2fr_1fr]">
        <Input label="Rôle" value={form.role_name} onChange={(e) => setForm({ ...form, role_name: e.target.value })} placeholder="Ex. Développeur·se frontend" error={error?.field("role_name")} />
        <Input label="Places" type="number" min={1} max={20} value={form.slots} onChange={(e) => setForm({ ...form, slots: e.target.value })} error={error?.field("slots")} />
      </div>
      <Input label="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      <Button type="submit" variant="secondary" disabled={!form.role_name.trim()}>Ajouter le rôle</Button>
    </form>
  );
}

export default function ProjectPage() {
  const { slug } = useParams<{ slug: string }>();
  const { status } = useAuth();
  const project = useApi<ProjectDetail>(`/projects/${slug}/`);
  const members = useApi<Paginated<Member>>(`/projects/${slug}/members/`, { page_size: 100 });
  const myRequests = useApi<Paginated<JoinRequest>>(status === "authenticated" ? "/join-requests/mine/" : null, { page_size: 100 });
  const [notice, setNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  if (project.loading && !project.data) return <Loading />;
  if (project.error) return <ErrorState error={project.error} onRetry={project.reload} />;
  if (!project.data) return null;
  const data = project.data;
  const pending = myRequests.data?.results.find((request) => request.project.slug === data.slug && request.status === "PENDING");

  async function changeStatus(target: string) {
    try {
      await api(`/projects/${data.slug}/`, { method: "PATCH", body: { status: target } });
      project.reload();
    } catch (caught) {
      setNotice({ kind: "error", text: (caught as ApiError).message });
    }
  }

  async function leave() {
    if (!window.confirm("Quitter ce projet ?")) return;
    try {
      await api(`/projects/${data.slug}/leave/`, { method: "POST" });
      project.reload();
      members.reload();
    } catch (caught) {
      setNotice({ kind: "error", text: (caught as ApiError).message });
    }
  }

  async function withdraw(id: string) {
    await api(`/join-requests/${id}/withdraw/`, { method: "POST" });
    myRequests.reload();
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      {notice && <Alert kind={notice.kind}>{notice.text}</Alert>}
      <Card>
        <div className="mb-2 flex flex-wrap gap-2">
          <Badge tone="brand">{label(PROJECT_STATUS, data.status)}</Badge>
          {data.my_role && <Badge tone="accent">Votre rôle : {label(PROJECT_ROLES, data.my_role)}</Badge>}
          {data.visibility === "PRIVATE" && <Badge>Privé</Badge>}
        </div>
        <h1 className="text-2xl font-semibold">{data.name}</h1>
        <p className="mt-1 text-muted">{data.short_description}</p>
        <div className="mt-3"><AuthorLine author={data.owner}><span>· propriétaire</span></AuthorLine></div>
        {data.problem && <><h2 className="mt-4 font-medium">Problématique</h2><p className="whitespace-pre-line text-sm">{data.problem}</p></>}
        {data.objectives && <><h2 className="mt-4 font-medium">Objectifs</h2><p className="whitespace-pre-line text-sm">{data.objectives}</p></>}
        {data.description && <div className="mt-4"><RichText html={data.description} /></div>}
        <div className="mt-4 flex flex-wrap gap-2">
          {data.technologies.map((technology) => <Badge key={technology.id}>{technology.name}</Badge>)}
        </div>
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          {data.repository_url && <a href={data.repository_url} target="_blank" rel="noopener noreferrer nofollow" className="text-brand-300 underline">Dépôt</a>}
          {data.demo_url && <a href={data.demo_url} target="_blank" rel="noopener noreferrer nofollow" className="text-brand-300 underline">Démonstration</a>}
          {data.expected_availability && <span className="text-muted">Disponibilité attendue : {data.expected_availability}</span>}
        </div>
        <div className="mt-4 text-xs text-muted">
          Avancement : {Object.entries(TASK_STATUS).map(([key, text]) => `${text} ${data.task_stats[key] ?? 0}`).join(" · ")}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-line pt-4">
          {data.permissions.view_tasks && <Link href={`/projets/${data.slug}/taches`} className="btn-primary rounded-xl px-4 py-2.5 text-sm">Tâches du projet</Link>}
          {data.permissions.manage_members && <Link href={`/projets/${data.slug}/demandes`} className="rounded-xl border border-line px-3 py-2 text-sm">Demandes reçues</Link>}
          {data.permissions.edit_settings && (
            <label className="text-sm">
              <span className="mr-2 text-muted">Statut</span>
              <select className="rounded-xl border border-line px-2 py-1.5 text-sm" value="" onChange={(e) => e.target.value && changeStatus(e.target.value)}>
                <option value="">Changer…</option>
                {(NEXT_STATUSES[data.status] ?? []).map((value) => <option key={value} value={value}>{label(PROJECT_STATUS, value)}</option>)}
              </select>
            </label>
          )}
          {data.my_role && data.my_role !== "OWNER" && <Button type="button" variant="ghost" className="text-rose-300" onClick={leave}>Quitter le projet</Button>}
          {!data.my_role && <span className="ml-auto"><ReportButton targetType="PROJECT" targetId={data.id} /></span>}
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 font-semibold">Rôles recherchés</h2>
        {data.role_needs.length === 0 && <p className="text-sm text-muted">Aucun rôle précis pour le moment.</p>}
        <ul className="space-y-2">
          {data.role_needs.map((need) => (
            <li key={need.id} className="rounded-xl border border-line px-3 py-2 text-sm">
              <span className="font-medium">{need.role_name}</span> · {need.slots} place(s) {need.is_open ? <Badge tone="brand">Ouvert</Badge> : <Badge>Pourvu</Badge>}
              {need.description && <p className="text-muted">{need.description}</p>}
            </li>
          ))}
        </ul>
        {data.permissions.manage_members && <RoleNeedForm slug={data.slug} onSaved={project.reload} />}
      </Card>

      <Card>
        <h2 className="mb-3 font-semibold">Équipe ({members.data?.count ?? data.member_count})</h2>
        <ul className="space-y-2">
          {members.data?.results.map((member) => (
            <li key={member.id} className="flex items-center justify-between">
              <AuthorLine author={member.user}>{member.title && <span>· {member.title}</span>}</AuthorLine>
              <Badge>{label(PROJECT_ROLES, member.role)}</Badge>
            </li>
          ))}
        </ul>
      </Card>

      {!data.my_role && (
        <Card>
          <h2 className="mb-3 font-semibold">Rejoindre l'équipe</h2>
          {status !== "authenticated" ? (
            <p className="text-sm text-muted"><Link href={`/connexion?next=/projets/${data.slug}`} className="text-brand-300 underline">Connectez-vous</Link> pour envoyer une demande.</p>
          ) : pending ? (
            <Alert>
              Votre demande est en attente de réponse.{" "}
              <button type="button" className="underline" onClick={() => withdraw(pending.id)}>La retirer</button>
            </Alert>
          ) : data.is_accepting_members ? (
            <JoinForm project={data} onSent={() => { myRequests.reload(); setNotice({ kind: "success", text: "Demande envoyée : le propriétaire va l'examiner." }); }} />
          ) : (
            <p className="text-sm text-muted">Ce projet n'accepte pas de nouveaux membres actuellement.</p>
          )}
        </Card>
      )}
    </div>
  );
}
