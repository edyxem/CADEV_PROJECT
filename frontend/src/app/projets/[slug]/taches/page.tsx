"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Button } from "@/components/ui/Button";
import { Alert, ErrorState, Loading } from "@/components/ui/Feedback";
import { Input, Select } from "@/components/ui/Field";
import { Badge, Card, PageTitle } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { Member, Paginated, ProjectDetail, Task } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { label, PRIORITY, TASK_STATUS } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

interface Column {
  status: string;
  label: string;
  tasks: Task[];
}

const STATUS_OPTIONS = Object.entries(TASK_STATUS).map(([value, text]) => ({ value, label: text }));

function TasksContent() {
  const { slug } = useParams<{ slug: string }>();
  const { user } = useAuth();
  const project = useApi<ProjectDetail>(`/projects/${slug}/`);
  const board = useApi<Column[]>(`/projects/${slug}/board/`);
  const members = useApi<Paginated<Member>>(`/projects/${slug}/members/`, { page_size: 100 });
  const [form, setForm] = useState({ title: "", assignee: "", priority: "MEDIUM" });
  const [error, setError] = useState<ApiError | null>(null);

  if (project.loading && !project.data) return <Loading />;
  if (project.error) return <ErrorState error={project.error} />;
  if (board.error) return <ErrorState error={board.error} onRetry={board.reload} />;
  const permissions = project.data?.permissions;
  // Un contributeur ne peut s'assigner que lui-même ; les observateurs ne reçoivent pas de tâche.
  const assignable = (members.data?.results ?? []).filter(
    (member) => member.role !== "OBSERVER" && (permissions?.manage_tasks || member.user.username === user?.username),
  );

  async function create(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api(`/projects/${slug}/tasks/`, { method: "POST", body: { ...form, assignee: form.assignee || null } });
      setForm({ title: "", assignee: "", priority: "MEDIUM" });
      board.reload();
    } catch (caught) {
      setError(caught as ApiError);
    }
  }

  async function changeStatus(task: Task, status: string) {
    setError(null);
    try {
      await api(`/tasks/${task.id}/`, { method: "PATCH", body: { status } });
      board.reload();
    } catch (caught) {
      setError(caught as ApiError);
    }
  }

  return (
    <div>
      <PageTitle title={`Tâches · ${project.data?.name ?? ""}`} subtitle="Réservé aux membres du projet." action={<Link href={`/projets/${slug}`} className="text-sm text-brand-700 underline">Retour au projet</Link>} />
      {error && error.code !== "validation_error" && <Alert kind="error">{error.message}</Alert>}
      {permissions?.create_tasks && (
        <Card className="mb-5">
          <form onSubmit={create} className="grid gap-x-3 sm:grid-cols-[2fr_1fr_1fr_auto] sm:items-end">
            <Input label="Nouvelle tâche" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} error={error?.field("title")} />
            <Select label="Assignée à" options={[{ value: "", label: "Personne" }, ...assignable.map((member) => ({ value: member.user.username, label: member.user.display_name }))]} value={form.assignee} onChange={(e) => setForm({ ...form, assignee: e.target.value })} />
            <Select label="Priorité" options={Object.entries(PRIORITY).map(([value, text]) => ({ value, label: text }))} value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} />
            <div className="mb-4"><Button type="submit" disabled={!form.title.trim()}>Ajouter</Button></div>
          </form>
        </Card>
      )}
      {board.loading && !board.data && <Loading />}
      <div className="grid gap-3 md:grid-cols-5">
        {board.data?.map((column) => (
          <section key={column.status} className="rounded-xl bg-stone-100 p-3" aria-label={column.label}>
            <h2 className="mb-2 text-sm font-semibold">{column.label} <span className="text-muted">({column.tasks.length})</span></h2>
            <div className="space-y-2">
              {column.tasks.map((task) => (
                <article key={task.id} className="rounded-lg border border-line bg-white p-3 text-sm shadow-sm">
                  <p className="font-medium">{task.title}</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    <Badge tone={task.priority === "HIGH" ? "danger" : "neutral"}>{label(PRIORITY, task.priority)}</Badge>
                    {task.assignee && <Badge tone="brand">{task.assignee.display_name}</Badge>}
                  </div>
                  {task.can_edit && (
                    <label className="mt-2 block text-xs">
                      <span className="sr-only">Statut de la tâche</span>
                      <select className="w-full rounded border border-line px-1 py-1" value={task.status} onChange={(e) => changeStatus(task, e.target.value)}>
                        {STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                      </select>
                    </label>
                  )}
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

export default function TasksPage() {
  return (
    <RequireAuth>
      <TasksContent />
    </RequireAuth>
  );
}
