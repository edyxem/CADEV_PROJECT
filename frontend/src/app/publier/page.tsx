"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Feedback";
import { Input, Select, Textarea } from "@/components/ui/Field";
import { Card, PageTitle } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { PostDetail } from "@/lib/api/types";
import { toOptions, useReferences } from "@/lib/references";
import { textToHtml } from "@/lib/text";

const TYPES = [
  { value: "DISCUSSION", label: "Discussion" },
  { value: "QUESTION", label: "Question" },
  { value: "ARTICLE", label: "Article / tutoriel" },
];

function PublishForm() {
  const router = useRouter();
  const initialType = useSearchParams().get("type") === "QUESTION" ? "QUESTION" : "DISCUSSION";
  const { categories, technologies } = useReferences();
  const [form, setForm] = useState({ type: initialType, title: "", category: "", content: "", environment: "" });
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState<"PUBLISHED" | "DRAFT" | null>(null);
  const isQuestion = form.type === "QUESTION";

  const update = (field: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((previous) => ({ ...previous, [field]: event.target.value }));

  async function submit(status: "PUBLISHED" | "DRAFT", event?: FormEvent) {
    event?.preventDefault();
    setSubmitting(status);
    setError(null);
    try {
      const post = await api<PostDetail>("/posts/", {
        method: "POST",
        body: {
          type: form.type,
          title: form.title,
          category: form.category,
          content: textToHtml(form.content),
          environment: isQuestion ? form.environment : "",
          technologies: selected,
          status,
        },
      });
      router.push(`/publications/${post.id}`);
    } catch (caught) {
      setError(caught as ApiError);
      setSubmitting(null);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageTitle title={isQuestion ? "Poser une question" : "Publier"} subtitle="Un titre précis et un contenu clair aident la communauté à vous répondre." />
      <Card>
        {error && <Alert kind="error">{error.code === "validation_error" ? "Vérifiez les champs signalés." : error.message}</Alert>}
        <form onSubmit={(event) => submit("PUBLISHED", event)} noValidate>
          <Select label="Type" options={TYPES} value={form.type} onChange={update("type")} />
          <Input label="Titre" value={form.title} onChange={update("title")} maxLength={150} hint="8 à 150 caractères." error={error?.field("title")} required />
          <Select label="Catégorie" options={toOptions(categories, "Choisir une catégorie")} value={form.category} onChange={update("category")} error={error?.field("category")} required />
          <Textarea
            label={isQuestion ? "Description du problème" : "Contenu"}
            value={form.content}
            onChange={update("content")}
            rows={10}
            hint="Ligne vide = nouveau paragraphe. `code` en ligne, ``` pour un bloc de code."
            error={error?.field("content")}
          />
          {isQuestion && (
            <Textarea label="Environnement (facultatif)" value={form.environment} onChange={update("environment")} rows={3} hint="Versions, système, ce que vous avez déjà essayé." />
          )}
          <fieldset className="mb-4">
            <legend className="text-sm font-medium">Technologies (8 au maximum)</legend>
            <div className="mt-2 flex max-h-40 flex-wrap gap-2 overflow-y-auto rounded-xl border border-line bg-panel p-2">
              {technologies.map((technology) => {
                const checked = selected.includes(technology.slug);
                return (
                  <label key={technology.id} className={`cursor-pointer rounded-full border px-2.5 py-1 text-xs ${checked ? "border-brand-400/60 bg-brand-50 text-brand-800" : "border-line"}`}>
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={checked}
                      onChange={() => setSelected((previous) => (checked ? previous.filter((slug) => slug !== technology.slug) : [...previous, technology.slug].slice(0, 8)))}
                    />
                    {technology.name}
                  </label>
                );
              })}
            </div>
            {error?.field("technologies") && <p className="mt-1 text-xs text-rose-300">{error.field("technologies")}</p>}
          </fieldset>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" loading={submitting === "PUBLISHED"} disabled={submitting !== null}>Publier</Button>
            <Button type="button" variant="secondary" loading={submitting === "DRAFT"} disabled={submitting !== null} onClick={() => submit("DRAFT")}>
              Enregistrer en brouillon
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

export default function PublishPage() {
  return (
    <RequireAuth>
      <Suspense>
        <PublishForm />
      </Suspense>
    </RequireAuth>
  );
}
