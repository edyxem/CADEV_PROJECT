"use client";

import Link from "next/link";

import { SpotlightCard } from "@/components/motion/Interactive";
import { Badge } from "@/components/ui/Misc";
import type { Opportunity } from "@/lib/api/types";
import { formatDay, label, OPPORTUNITY_TYPES, WORK_MODES } from "@/lib/labels";

/** Nombre de jours restants avant la date limite (null si aucune). */
export function daysLeft(deadline: string | null): number | null {
  if (!deadline) return null;
  const end = new Date(`${deadline}T23:59:59`).getTime();
  return Math.ceil((end - Date.now()) / 86_400_000);
}

export function OpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  const remaining = daysLeft(opportunity.deadline);
  const urgent = remaining !== null && remaining >= 0 && remaining <= 7;
  return (
    <SpotlightCard className="h-full p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge tone="accent">{label(OPPORTUNITY_TYPES, opportunity.type)}</Badge>
        <Badge>{label(WORK_MODES, opportunity.work_mode)}</Badge>
        {opportunity.is_verified_partner && <Badge tone="brand">✓ Partenaire vérifié</Badge>}
      </div>
      <h3 className="font-display text-lg font-semibold leading-snug">
        <Link href={`/opportunites/${opportunity.id}`} className="after:absolute after:inset-0 hover:text-brand-200">
          {opportunity.title}
        </Link>
      </h3>
      <p className="mt-1 text-sm text-muted">
        {opportunity.organization_label || opportunity.publisher.display_name}
        {opportunity.country ? ` · ${opportunity.country.name}` : ""}
        {opportunity.location ? ` · ${opportunity.location}` : ""}
      </p>
      {opportunity.technologies.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {opportunity.technologies.map((technology) => (
            <span key={technology.id} className="rounded-md bg-white/[0.04] px-2 py-0.5 font-mono text-[11px] text-muted">
              {technology.name}
            </span>
          ))}
        </div>
      )}
      {opportunity.deadline && (
        <p className={`mt-4 flex items-center gap-2 text-xs ${opportunity.is_expired ? "text-muted line-through" : urgent ? "text-ocre-300" : "text-muted"}`}>
          {urgent && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ocre-400" aria-hidden />}
          Date limite : {formatDay(opportunity.deadline)}
          {urgent && remaining !== null && ` (J-${remaining})`}
        </p>
      )}
    </SpotlightCard>
  );
}
