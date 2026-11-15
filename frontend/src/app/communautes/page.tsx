"use client";

import Link from "next/link";
import { useState } from "react";

import { JoinButton } from "@/components/communities/JoinButton";
import { SpotlightCard } from "@/components/motion/Interactive";
import { Stagger, StaggerItem } from "@/components/motion/Reveal";
import { EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/Field";
import { Badge, PageTitle, Pagination } from "@/components/ui/Misc";
import type { CommunityItem, Paginated } from "@/lib/api/types";
import { COMMUNITY_KINDS, label } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

const ICONS: Record<string, string> = { COUNTRY: "🌍", CITY: "🏙️", UNIVERSITY: "🎓", TECHNOLOGY: "⚙️", DOMAIN: "🧭" };

function CommunityCard({ initial }: { initial: CommunityItem }) {
  const [community, setCommunity] = useState(initial);
  return (
    <SpotlightCard className="h-full p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-ink/5 text-2xl" aria-hidden>
          {ICONS[community.kind] ?? "✦"}
        </span>
        <div className="min-w-0">
          <Badge tone="accent">{label(COMMUNITY_KINDS, community.kind)}</Badge>
          <h3 className="mt-1 font-display text-lg font-semibold leading-snug">
            <Link href={`/communautes/${community.slug}`} className="after:absolute after:inset-0 hover:text-brand-200">
              {community.name}
            </Link>
          </h3>
        </div>
      </div>
      {community.description && <p className="mt-3 line-clamp-2 text-sm text-muted">{community.description}</p>}
      <div className="mt-4 flex items-center justify-between gap-2">
        <p className="text-xs text-muted">{community.member_count} membre(s)</p>
        <JoinButton community={community} onChange={setCommunity} />
      </div>
    </SpotlightCard>
  );
}

export default function CommunitiesPage() {
  const [kind, setKind] = useState("");
  const [page, setPage] = useState(1);
  const result = useApi<Paginated<CommunityItem>>("/communities/", { kind: kind || undefined, page });

  return (
    <div>
      <PageTitle eyebrow="Communautés" title="Se retrouver entre pairs" subtitle="Rejoignez les développeurs de votre pays, de votre ville, de votre université ou autour d'une technologie." />
      <div className="max-w-xs">
        <Select
          label="Type de communauté"
          options={[{ value: "", label: "Toutes" }, ...Object.entries(COMMUNITY_KINDS).map(([value, text]) => ({ value, label: text }))]}
          value={kind}
          onChange={(e) => {
            setKind(e.target.value);
            setPage(1);
          }}
        />
      </div>
      {result.loading && !result.data && <Loading />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {result.data?.count === 0 && <EmptyState title="Aucune communauté de ce type">Les responsables de la plateforme créent de nouvelles communautés régulièrement.</EmptyState>}
      <Stagger key={JSON.stringify([kind, page, result.data?.count])} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {result.data?.results.map((community) => (
          <StaggerItem key={community.id}>
            <CommunityCard initial={community} />
          </StaggerItem>
        ))}
      </Stagger>
      {result.data && <Pagination page={page} count={result.data.count} onChange={setPage} />}
    </div>
  );
}
