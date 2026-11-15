"use client";

import { useState, type FormEvent } from "react";

import { Stagger, StaggerItem } from "@/components/motion/Reveal";
import { PostCard } from "@/components/community/PostCard";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/Field";
import { PageTitle, Pagination } from "@/components/ui/Misc";
import type { Paginated, Post } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { toOptions, useReferences } from "@/lib/references";
import { useApi } from "@/lib/useApi";

const ORDERINGS = [
  { value: "recent", label: "Récentes" },
  { value: "active", label: "Actives" },
  { value: "popular", label: "Populaires (30 jours)" },
  { value: "unanswered", label: "Sans réponse" },
];

const TYPES = [
  { value: "", label: "Tous les types" },
  { value: "DISCUSSION", label: "Discussions" },
  { value: "QUESTION", label: "Questions" },
  { value: "ARTICLE", label: "Articles" },
  { value: "ANNOUNCEMENT", label: "Annonces" },
];

export function FeedView({ questionsOnly = false }: { questionsOnly?: boolean }) {
  const { status } = useAuth();
  const { categories, technologies } = useReferences();
  const [filters, setFilters] = useState({ type: "", category: "", technology: "", ordering: "recent" });
  const [draft, setDraft] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  // Avec des mots-clés, on utilise la recherche plein texte classée par pertinence.
  const path = search ? "/search/posts/" : questionsOnly ? "/questions/" : "/posts/";
  const feed = useApi<Paginated<Post>>(path, {
    ...filters,
    type: questionsOnly ? "QUESTION" : filters.type,
    ordering: search ? undefined : filters.ordering,
    q: search || undefined,
    page,
  });

  const update = (field: keyof typeof filters) => (event: React.ChangeEvent<HTMLSelectElement>) => {
    setFilters((previous) => ({ ...previous, [field]: event.target.value }));
    setPage(1);
  };

  function onSearch(event: FormEvent) {
    event.preventDefault();
    setSearch(draft.trim());
    setPage(1);
  }

  return (
    <div>
      <PageTitle
        title={questionsOnly ? "Questions" : "Fil communautaire"}
        subtitle={questionsOnly ? "Entraide technique : posez vos questions, répondez à celles des autres." : "Les échanges récents de la communauté."}
        action={status === "authenticated" ? <ButtonLink href={questionsOnly ? "/publier?type=QUESTION" : "/publier"}>{questionsOnly ? "Poser une question" : "Publier"}</ButtonLink> : undefined}
      />

      <form onSubmit={onSearch} className="mb-4 flex gap-2" role="search">
        <label htmlFor="feed-search" className="sr-only">Rechercher</label>
        <input id="feed-search" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Rechercher (ex. pagination django)" className="w-full rounded-xl border border-line bg-panel px-3 py-2 text-sm" />
        <button type="submit" className="btn-primary rounded-xl px-5 py-2.5 text-sm">Rechercher</button>
      </form>
      {search && (
        <p className="mb-4 text-sm text-muted">
          Résultats pour « {search} » —{" "}
          <button type="button" className="text-brand-300 underline" onClick={() => { setSearch(""); setDraft(""); }}>effacer</button>
        </p>
      )}

      <div className="grid gap-x-3 sm:grid-cols-2 lg:grid-cols-4">
        {!questionsOnly && <Select label="Type" options={TYPES} value={filters.type} onChange={update("type")} />}
        <Select label="Catégorie" options={toOptions(categories, "Toutes")} value={filters.category} onChange={update("category")} />
        <Select label="Technologie" options={toOptions(technologies, "Toutes")} value={filters.technology} onChange={update("technology")} />
        {!search && <Select label="Tri" options={questionsOnly ? ORDERINGS : ORDERINGS.slice(0, 3)} value={filters.ordering} onChange={update("ordering")} />}
      </div>

      {feed.loading && !feed.data && <Loading />}
      {feed.error && <ErrorState error={feed.error} onRetry={feed.reload} />}
      {feed.data && feed.data.count === 0 && (
        <EmptyState title="Aucun résultat">Modifiez les filtres ou lancez la première discussion.</EmptyState>
      )}
      <Stagger key={JSON.stringify([filters, search, page, feed.data?.count])} className={`space-y-3 transition-opacity ${feed.loading ? "opacity-60" : ""}`}>
        {feed.data?.results.map((post) => (
          <StaggerItem key={post.id}>
            <PostCard post={post} />
          </StaggerItem>
        ))}
      </Stagger>
      {feed.data && <Pagination page={page} count={feed.data.count} onChange={setPage} />}
    </div>
  );
}
