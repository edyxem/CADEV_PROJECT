"use client";

import { AnimatePresence, LayoutGroup, motion } from "motion/react";
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
  // Déplacements optimistes : la carte change de colonne avant la réponse de l'API.
  const [moves, setMoves] = useState<Record<string, string>>({});
  const [dragging, setDragging] = useState<string | null>(null);
  const [over, setOver] = useState<string | null>(null);

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
    if (task.status === status && !moves[task.id]) return;
    setError(null);
    setMoves((current) => ({ ...current, [task.id]: status }));
    try {
      await api(`/tasks/${task.id}/`, { method: "PATCH", body: { status } });
      board.reload();
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setMoves((current) => {
        const next = { ...current };
        delete next[task.id];
        return next;
      });
    }
  }

  const allTasks = board.data?.flatMap((column) => column.tasks) ?? [];
  const columns = (board.data ?? []).map((column) => ({
    ...column,
    tasks: allTasks.filter((task) => (moves[task.id] ?? task.status) === column.status),
  }));

  function drop(status: string) {
    const task = allTasks.find((candidate) => candidate.id === dragging);
    setDragging(null);
    setOver(null);
    if (task && task.can_edit && (moves[task.id] ?? task.status) !== status) changeStatus(task, status);
  }

  return (
    <div>
      <PageTitle title={`Tâches · ${project.data?.name ?? ""}`} subtitle="Réservé aux membres du projet." action={<Link href={`/projets/${slug}`} className="text-sm text-brand-300 underline">Retour au projet</Link>} />
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
      {columns.length > 0 && <p className="mb-3 text-xs text-muted">Glissez une carte vers une autre colonne, ou utilisez le sélecteur de statut.</p>}
      <LayoutGroup>
        <div className="grid gap-3 md:grid-cols-5">
          {columns.map((column) => (
            <section
              key={column.status}
              aria-label={column.label}
              onDragOver={(event) => {
                if (!dragging) return;
                event.preventDefault();
                setOver(column.status);
              }}
              onDragLeave={() => setOver((current) => (current === column.status ? null : current))}
              onDrop={(event) => {
                event.preventDefault();
                drop(column.status);
              }}
              className={`min-h-40 rounded-2xl border p-3 transition-colors ${over === column.status ? "border-brand-400/60 bg-brand-500/10" : "border-transparent bg-panel-2"}`}
            >
              <h2 className="mb-3 flex items-center justify-between text-sm font-semibold">
                {column.label}
                <span className="rounded-full bg-white/5 px-2 py-0.5 text-xs text-muted">{column.tasks.length}</span>
              </h2>
              <div className="space-y-2">
                <AnimatePresence initial={false}>
                  {column.tasks.map((task) => (
                    <motion.div
                      key={task.id}
                      layout
                      layoutId={`task-${task.id}`}
                      initial={{ opacity: 0, scale: 0.96 }}
                      animate={{ opacity: dragging === task.id ? 0.45 : 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.96 }}
                      transition={{ type: "spring", stiffness: 420, damping: 34 }}
                    >
                      <article
                        draggable={task.can_edit}
                        onDragStart={(event) => {
                          event.dataTransfer.setData("text/plain", task.id);
                          event.dataTransfer.effectAllowed = "move";
                          setDragging(task.id);
                        }}
                        onDragEnd={() => {
                          setDragging(null);
                          setOver(null);
                        }}
                        className={`rounded-xl border border-line bg-panel p-3 text-sm shadow-sm ${task.can_edit ? "cursor-grab active:cursor-grabbing hover:border-brand-400/40" : ""}`}
                      >
                        <p className="font-medium">{task.title}</p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          <Badge tone={task.priority === "HIGH" ? "danger" : "neutral"}>{label(PRIORITY, task.priority)}</Badge>
                          {task.assignee && <Badge tone="brand">{task.assignee.display_name}</Badge>}
                        </div>
                        {task.can_edit && (
                          <label className="mt-2 block text-xs">
                            <span className="sr-only">Statut de la tâche</span>
                            <select className="w-full rounded-lg border border-line bg-panel-2 px-1 py-1" value={moves[task.id] ?? task.status} onChange={(e) => changeStatus(task, e.target.value)}>
                              {STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                            </select>
                          </label>
                        )}
                      </article>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </section>
          ))}
        </div>
      </LayoutGroup>
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
