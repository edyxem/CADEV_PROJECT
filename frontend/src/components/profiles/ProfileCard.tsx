import Link from "next/link";

import { Avatar, Badge, Card } from "@/components/ui/Misc";
import type { Profile } from "@/lib/api/types";
import { AVAILABILITY, label, LEVELS } from "@/lib/labels";

export function ProfileCard({ profile }: { profile: Profile }) {
  return (
    <Card>
      <div className="flex items-start gap-3">
        <Avatar author={profile} size={48} />
        <div className="min-w-0 flex-1">
          <Link href={`/membres/${profile.username}`} className="font-semibold hover:underline">
            {profile.display_name}
          </Link>
          <p className="text-xs text-muted">@{profile.username}</p>
          {profile.headline && <p className="mt-1 text-sm">{profile.headline}</p>}
          <div className="mt-2 flex flex-wrap gap-1">
            {profile.country && <Badge>{profile.country.name}</Badge>}
            {profile.experience_level && <Badge>{label(LEVELS, profile.experience_level)}</Badge>}
            {profile.availability_status && profile.availability_status !== "NOT_AVAILABLE" && (
              <Badge tone="brand">{label(AVAILABILITY, profile.availability_status)}</Badge>
            )}
          </div>
          {profile.skills && profile.skills.length > 0 && (
            <p className="mt-2 truncate text-xs text-muted">
              {profile.skills.map((skill) => skill.technology.name).join(" · ")}
            </p>
          )}
        </div>
      </div>
    </Card>
  );
}
