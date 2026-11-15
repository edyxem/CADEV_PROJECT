"use client";

import { useState } from "react";

import { Stagger, StaggerItem } from "@/components/motion/Reveal";
import { OpportunityCard } from "@/components/opportunities/OpportunityCard";
import { EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/Field";
import { PageTitle, Pagination } from "@/components/ui/Misc";
import type { Opportunity, Paginated } from "@/lib/api/types";
import { OPPORTUNITY_TYPES, WORK_MODES } from "@/lib/labels";
import { toOptions, useReferences } from "@/lib/references";
import { useApi } from "@/lib/useApi";

const entries = (map: Record<string, string>, empty: string) => [{ value: "", label: empty }, ...Object.entries(map).map(([value, text]) => ({ value, label: text }))];

export default function OpportunitiesPage() {
  const { technologies, countries } = useReferences();
  const [filters, setFilters] = useState({ type: "", work_mode: "", technology: "", country: "", include_expired: "" });
  const [page, setPage] = useState(1);
  const result = useApi<Paginated<Opportunity>>("/opportunities/", { ...filters, page });

  const update = (field: keyof typeof filters) => (event: React.ChangeEvent<HTMLSelectElement>) => {
    setFilters((previous) => ({ ...previous, [field]: event.target.value }));
    setPage(1);
  };

  return (
    <div>
      <PageTitle
        eyebrow="Opportunités"
        title="Faire grandir sa carrière"
        subtitle="Emplois, stages, missions, bourses, hackathons et programmes publiés par la communauté et ses partenaires. Chaque annonce est vérifiée avant publication."
      />
      <div className="grid gap-x-3 sm:grid-cols-2 lg:grid-cols-5">
        <Select label="Type" options={entries(OPPORTUNITY_TYPES, "Tous les types")} value={filters.type} onChange={update("type")} />
        <Select label="Mode de travail" options={entries(WORK_MODES, "Tous")} value={filters.work_mode} onChange={update("work_mode")} />
        <Select label="Technologie" options={toOptions(technologies, "Toutes")} value={filters.technology} onChange={update("technology")} />
        <Select label="Pays" options={[{ value: "", label: "Tous" }, ...countries.map((country) => ({ value: country.code, label: country.name }))]} value={filters.country} onChange={update("country")} />
        <Select label="Annonces expirées" options={[{ value: "", label: "Masquées" }, { value: "true", label: "Affichées" }]} value={filters.include_expired} onChange={update("include_expired")} />
      </div>
      {result.loading && !result.data && <Loading />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {result.data?.count === 0 && <EmptyState title="Aucune opportunité pour ces critères">Élargissez les filtres ou revenez bientôt.</EmptyState>}
      <Stagger key={JSON.stringify([filters, page, result.data?.count])} className={`grid gap-3 transition-opacity sm:grid-cols-2 ${result.loading ? "opacity-60" : ""}`}>
        {result.data?.results.map((opportunity) => (
          <StaggerItem key={opportunity.id}>
            <OpportunityCard opportunity={opportunity} />
          </StaggerItem>
        ))}
      </Stagger>
      {result.data && <Pagination page={page} count={result.data.count} onChange={setPage} />}
    </div>
  );
}
