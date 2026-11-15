"use client";

import Link from "next/link";

import { SpotlightCard } from "@/components/motion/Interactive";
import { Avatar, Badge } from "@/components/ui/Misc";
import type { Profile } from "@/lib/api/types";
import { AVAILABILITY, label, LEVELS } from "@/lib/labels";

export function ProfileCard({ profile }: { profile: Profile }) {
  const available = profile.availability_status && profile.availability_status !== "NOT_AVAILABLE";
  return (
    <SpotlightCard className="h-full p-5" glow={available ? "16 185 129" : "245 158 11"}>
      <div className="flex items-start gap-4">
        <div className="relative">
          <Avatar author={profile} size={52} />
          {available && <span className="absolute -bottom-0.5 -right-0.5 h-3.5 w-3.5 rounded-full border-2 border-panel bg-brand-400" title="Disponible" />}
        </div>
        <div className="min-w-0 flex-1">
          <Link href={`/membres/${profile.username}`} className="font-display text-lg font-semibold after:absolute after:inset-0 hover:text-brand-200">
            {profile.display_name}
          </Link>
          <p className="text-xs text-muted">@{profile.username}</p>
          {profile.headline && <p className="mt-1.5 text-sm text-ink/85">{profile.headline}</p>}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {profile.country && <Badge>{profile.country.name}</Badge>}
            {profile.experience_level && <Badge>{label(LEVELS, profile.experience_level)}</Badge>}
            {available && <Badge tone="brand">{label(AVAILABILITY, profile.availability_status)}</Badge>}
          </div>
          {profile.skills && profile.skills.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {profile.skills.slice(0, 5).map((skill) => (
                <span key={skill.id} className="rounded-md bg-white/[0.04] px-2 py-0.5 font-mono text-[11px] text-muted">{skill.technology.name}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    </SpotlightCard>
  );
}
