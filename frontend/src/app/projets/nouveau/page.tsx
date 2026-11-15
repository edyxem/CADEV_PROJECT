"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Feedback";
import { Input, Select, Textarea } from "@/components/ui/Field";
import { Card, PageTitle } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { ProjectDetail } from "@/lib/api/types";
import { useReferences } from "@/lib/references";
import { textToHtml } from "@/lib/text";

const MODES = [
  { value: "REMOTE", label: "À distance" },
  { value: "HYBRID", label: "Hybride" },
  { value: "ONSITE", label: "Présentiel" },
];

function NewProjectForm() {
  const router = useRouter();
  const { technologies } = useReferences();
  const [form, setForm] = useState({
    name: "",
    short_description: "",
    description: "",
    problem: "",
    objectives: "",
    collaboration_mode: "REMOTE",
    expected_availability: "",
    repository_url: "",
    demo_url: "",
  });
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);

  const update = (field: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((previous) => ({ ...previous, [field]: event.target.value }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const project = await api<ProjectDetail>("/projects/", {
        method: "POST",
        body: { ...form, description: textToHtml(form.description), technologies: selected, status: "RECRUITING" },
      });
      router.push(`/projets/${project.slug}`);
    } catch (caught) {
      setError(caught as ApiError);
      setPending(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageTitle title="Créer un projet" subtitle="Décrivez le besoin : vous deviendrez propriétaire et pourrez ajouter les rôles recherchés." />
      <Card>
        {error && <Alert kind="error">{error.code === "validation_error" ? "Vérifiez les champs signalés." : error.message}</Alert>}
        <form onSubmit={submit} noValidate>
          <Input label="Nom du projet" value={form.name} onChange={update("name")} error={error?.field("name")} required />
          <Input label="Résumé" value={form.short_description} onChange={update("short_description")} maxLength={240} error={error?.field("short_description")} required />
          <Textarea label="Problématique ou besoin visé" value={form.problem} onChange={update("problem")} rows={3} />
          <Textarea label="Objectifs et résultat recherché" value={form.objectives} onChange={update("objectives")} rows={3} />
          <Textarea label="Description" value={form.description} onChange={update("description")} rows={6} />
          <div className="grid gap-x-3 sm:grid-cols-2">
            <Select label="Mode de collaboration" options={MODES} value={form.collaboration_mode} onChange={update("collaboration_mode")} />
            <Input label="Disponibilité attendue" value={form.expected_availability} onChange={update("expected_availability")} placeholder="Ex. 5 h par semaine" />
            <Input label="Dépôt (GitHub, GitLab…)" type="url" value={form.repository_url} onChange={update("repository_url")} error={error?.field("repository_url")} />
            <Input label="Lien de démonstration" type="url" value={form.demo_url} onChange={update("demo_url")} error={error?.field("demo_url")} />
          </div>
          <fieldset className="mb-4">
            <legend className="text-sm font-medium">Technologies</legend>
            <div className="mt-2 flex max-h-40 flex-wrap gap-2 overflow-y-auto rounded-lg border border-line bg-white p-2">
              {technologies.map((technology) => {
                const checked = selected.includes(technology.slug);
                return (
                  <label key={technology.id} className={`cursor-pointer rounded-full border px-2.5 py-1 text-xs ${checked ? "border-brand-600 bg-brand-50 text-brand-800" : "border-line"}`}>
                    <input type="checkbox" className="sr-only" checked={checked} onChange={() => setSelected((previous) => (checked ? previous.filter((s) => s !== technology.slug) : [...previous, technology.slug].slice(0, 12)))} />
                    {technology.name}
                  </label>
                );
              })}
            </div>
          </fieldset>
          <Button type="submit" loading={pending}>Créer le projet</Button>
        </form>
      </Card>
    </div>
  );
}

export default function NewProjectPage() {
  return (
    <RequireAuth>
      <NewProjectForm />
    </RequireAuth>
  );
}
