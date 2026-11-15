import Link from "next/link";

import { Badge, Card } from "@/components/ui/Misc";
import type { Project } from "@/lib/api/types";
import { label, PROJECT_STATUS } from "@/lib/labels";

export function ProjectCard({ project }: { project: Project }) {
  return (
    <Card>
      <div className="mb-2 flex flex-wrap gap-2">
        <Badge tone={project.is_accepting_members ? "brand" : "neutral"}>{label(PROJECT_STATUS, project.status)}</Badge>
        {project.is_accepting_members && project.open_role_count > 0 && (
          <Badge tone="accent">{project.open_role_count} rôle(s) recherché(s)</Badge>
        )}
      </div>
      <h3 className="font-semibold">
        <Link href={`/projets/${project.slug}`} className="hover:text-brand-700 hover:underline">
          {project.name}
        </Link>
      </h3>
      <p className="mt-1 line-clamp-2 text-sm text-muted">{project.short_description}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {project.technologies.map((technology) => (
          <span key={technology.id} className="rounded bg-stone-100 px-1.5 py-0.5 text-xs">{technology.name}</span>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted">
        Porté par {project.owner.display_name} · {project.member_count} membre(s)
      </p>
    </Card>
  );
}
