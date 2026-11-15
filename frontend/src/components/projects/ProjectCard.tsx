"use client";

import Link from "next/link";

import { SpotlightCard } from "@/components/motion/Interactive";
import { Badge } from "@/components/ui/Misc";
import type { Project } from "@/lib/api/types";
import { label, PROJECT_STATUS } from "@/lib/labels";

export function ProjectCard({ project }: { project: Project }) {
  return (
    <SpotlightCard className="h-full p-5" tilt={false} glow={project.is_accepting_members ? "16 185 129" : "148 163 184"}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge tone={project.is_accepting_members ? "brand" : "neutral"}>
          {project.is_accepting_members && <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-brand-400" />}
          {label(PROJECT_STATUS, project.status)}
        </Badge>
        {project.is_accepting_members && project.open_role_count > 0 && (
          <Badge tone="accent">{project.open_role_count} rôle(s) recherché(s)</Badge>
        )}
      </div>
      <h3 className="font-display text-lg font-semibold">
        <Link href={`/projets/${project.slug}`} className="after:absolute after:inset-0 hover:text-brand-200">
          {project.name}
        </Link>
      </h3>
      <p className="mt-1.5 line-clamp-2 text-sm text-muted">{project.short_description}</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {project.technologies.map((technology) => (
          <span key={technology.id} className="rounded-md bg-white/[0.04] px-2 py-0.5 font-mono text-[11px] text-muted">{technology.name}</span>
        ))}
      </div>
      <p className="mt-4 text-xs text-muted">
        Porté par <span className="text-ink">{project.owner.display_name}</span> · {project.member_count} membre(s)
      </p>
    </SpotlightCard>
  );
}
