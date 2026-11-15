"use client";

import { Stagger, StaggerItem } from "@/components/motion/Reveal";
import { useState, type FormEvent } from "react";

import { ProjectCard } from "@/components/projects/ProjectCard";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/Field";
import { PageTitle, Pagination } from "@/components/ui/Misc";
import type { Paginated, Project } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { PROJECT_STATUS } from "@/lib/labels";
import { toOptions, useReferences } from "@/lib/references";
import { useApi } from "@/lib/useApi";

export default function ProjectsPage() {
  const { status } = useAuth();
  const { technologies } = useReferences();
  const [filters, setFilters] = useState({ recruiting: "", technology: "", status: "" });
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const result = useApi<Paginated<Project>>(q ? "/search/projects/" : "/projects/", { ...filters, q: q || undefined, page });

  const update = (field: keyof typeof filters) => (event: React.ChangeEvent<HTMLSelectElement>) => {
    setFilters((previous) => ({ ...previous, [field]: event.target.value }));
    setPage(1);
  };

  function onSearch(event: FormEvent) {
    event.preventDefault();
    setQ(draft.trim());
    setPage(1);
  }

  return (
    <div>
      <PageTitle
        title="Projets"
        subtitle="Rejoignez une équipe ou lancez un appel à collaboration."
        action={status === "authenticated" ? <ButtonLink href="/projets/nouveau">Créer un projet</ButtonLink> : undefined}
      />
      <form onSubmit={onSearch} className="mb-4 flex gap-2" role="search">
        <label htmlFor="project-search" className="sr-only">Rechercher un projet</label>
        <input id="project-search" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Nom, objectif, domaine…" className="w-full rounded-xl border border-line bg-panel px-3 py-2 text-sm" />
        <button type="submit" className="btn-primary rounded-xl px-5 py-2.5 text-sm">Rechercher</button>
      </form>
      <div className="grid gap-x-3 sm:grid-cols-3">
        <Select label="Recrutement" options={[{ value: "", label: "Tous" }, { value: "true", label: "Accepte des membres" }, { value: "false", label: "Équipe complète" }]} value={filters.recruiting} onChange={update("recruiting")} />
        <Select label="Technologie" options={toOptions(technologies, "Toutes")} value={filters.technology} onChange={update("technology")} />
        <Select label="Statut" options={[{ value: "", label: "Tous" }, ...Object.entries(PROJECT_STATUS).filter(([v]) => v !== "ARCHIVED").map(([value, text]) => ({ value, label: text }))]} value={filters.status} onChange={update("status")} />
      </div>
      {result.loading && !result.data && <Loading />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {result.data?.count === 0 && <EmptyState title="Aucun projet trouvé">Soyez le premier à lancer un appel à collaboration.</EmptyState>}
      <Stagger key={JSON.stringify([filters, q, page, result.data?.count])} className={`grid gap-3 sm:grid-cols-2 transition-opacity ${result.loading ? "opacity-60" : ""}`}>
        {result.data?.results.map((project) => (
          <StaggerItem key={project.id}>
            <ProjectCard project={project} />
          </StaggerItem>
        ))}
      </Stagger>
      {result.data && <Pagination page={page} count={result.data.count} onChange={setPage} />}
    </div>
  );
}
