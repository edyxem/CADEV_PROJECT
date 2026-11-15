"use client";

import { useState, type FormEvent } from "react";

import { ProfileCard } from "@/components/profiles/ProfileCard";
import { EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/Field";
import { PageTitle, Pagination } from "@/components/ui/Misc";
import type { Paginated, Profile } from "@/lib/api/types";
import { AVAILABILITY, LEVELS } from "@/lib/labels";
import { toOptions, useReferences } from "@/lib/references";
import { useApi } from "@/lib/useApi";

const fromMap = (map: Record<string, string>, empty: string) => [
  { value: "", label: empty },
  ...Object.entries(map).map(([value, text]) => ({ value, label: text })),
];

export default function DirectoryPage() {
  const { technologies, countries } = useReferences();
  const [filters, setFilters] = useState({ technology: "", country: "", availability: "", level: "" });
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const result = useApi<Paginated<Profile>>(q ? "/search/users/" : "/profiles/", { ...filters, q: q || undefined, page });

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
      <PageTitle title="Développeurs" subtitle="Trouvez des pairs et des collaborateurs. Les compétences sont déclarées par les membres." />
      <form onSubmit={onSearch} className="mb-4 flex gap-2" role="search">
        <label htmlFor="people-search" className="sr-only">Rechercher un membre</label>
        <input id="people-search" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Nom, titre, biographie…" className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm" />
        <button type="submit" className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white">Rechercher</button>
      </form>
      <div className="grid gap-x-3 sm:grid-cols-2 lg:grid-cols-4">
        <Select label="Technologie" options={toOptions(technologies, "Toutes")} value={filters.technology} onChange={update("technology")} />
        <Select label="Pays" options={[{ value: "", label: "Tous" }, ...countries.map((c) => ({ value: c.code, label: c.name }))]} value={filters.country} onChange={update("country")} />
        <Select label="Disponibilité" options={fromMap(AVAILABILITY, "Toutes")} value={filters.availability} onChange={update("availability")} />
        <Select label="Niveau déclaré" options={fromMap(LEVELS, "Tous")} value={filters.level} onChange={update("level")} />
      </div>
      {result.loading && !result.data && <Loading />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {result.data?.count === 0 && <EmptyState title="Aucun profil ne correspond">Élargissez les filtres.</EmptyState>}
      <div className={`grid gap-3 sm:grid-cols-2 ${result.loading ? "opacity-60" : ""}`}>
        {result.data?.results.map((profile) => <ProfileCard key={profile.username} profile={profile} />)}
      </div>
      {result.data && <Pagination page={page} count={result.data.count} onChange={setPage} />}
    </div>
  );
}
