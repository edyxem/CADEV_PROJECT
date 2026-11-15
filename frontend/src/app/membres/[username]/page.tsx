"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { ReportButton } from "@/components/community/Actions";
import { ProjectCard } from "@/components/projects/ProjectCard";
import { ButtonLink } from "@/components/ui/Button";
import { ErrorState, Loading } from "@/components/ui/Feedback";
import { Avatar, Badge, Card } from "@/components/ui/Misc";
import type { Paginated, Profile, Project } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { AVAILABILITY, formatDate, label, LEVELS } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

interface Reputation {
  score: number;
  breakdown: { event_type: string; label: string; count: number; points: number }[];
  achievements: { code: string; name: string; description: string }[];
  explanation: string;
}

export default function MemberPage() {
  const { username } = useParams<{ username: string }>();
  const { user } = useAuth();
  const profile = useApi<Profile>(`/profiles/${username}/`);
  const visible = profile.data && !profile.data.is_private;
  const reputation = useApi<Reputation>(visible ? `/profiles/${username}/reputation/` : null);
  const projects = useApi<Paginated<Project>>(visible ? "/projects/" : null, { member: username });

  if (profile.loading && !profile.data) return <Loading />;
  if (profile.error) return <ErrorState error={profile.error} onRetry={profile.reload} />;
  if (!profile.data) return null;
  const data = profile.data;
  const isMe = user?.username === data.username;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Card>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          <Avatar author={data} size={80} />
          <div className="flex-1">
            <h1 className="text-2xl font-semibold">{data.display_name}</h1>
            <p className="text-sm text-muted">@{data.username}</p>
            {data.is_private ? (
              <p className="mt-3 text-sm text-muted">Ce profil est privé.</p>
            ) : (
              <>
                {data.headline && <p className="mt-2">{data.headline}</p>}
                <div className="mt-3 flex flex-wrap gap-2">
                  {data.country && <Badge>{data.country.name}{data.city ? ` · ${data.city}` : ""}</Badge>}
                  {data.experience_level && <Badge>Niveau déclaré : {label(LEVELS, data.experience_level)}</Badge>}
                  {data.availability_status && <Badge tone="brand">{label(AVAILABILITY, data.availability_status)}</Badge>}
                  {data.languages?.map((language) => <Badge key={language}>{language.toUpperCase()}</Badge>)}
                </div>
                {data.bio && <p className="mt-3 whitespace-pre-line text-sm">{data.bio}</p>}
                <p className="mt-3 text-xs text-muted">Membre depuis {formatDate(data.member_since)}</p>
              </>
            )}
          </div>
          {isMe ? (
            <ButtonLink href="/parametres" variant="secondary">Modifier mon profil</ButtonLink>
          ) : (
            <div className="flex flex-col items-end gap-2">
              {user && (
                <ButtonLink href={`/messages?to=${data.username}`} variant="secondary">
                  Envoyer un message
                </ButtonLink>
              )}
              {data.user_id && <ReportButton targetType="PROFILE" targetId={data.user_id} />}
            </div>
          )}
        </div>
      </Card>

      {visible && (
        <>
          <Card>
            <h2 className="mb-1 font-semibold">Compétences</h2>
            <p className="mb-3 text-xs text-muted">Déclarées par le membre ; « preuve ajoutée » ne signifie pas « vérifiée ».</p>
            {data.skills?.length ? (
              <ul className="grid gap-2 sm:grid-cols-2">
                {data.skills.map((skill) => (
                  <li key={skill.id} className="flex items-center justify-between rounded-xl border border-line px-3 py-2 text-sm">
                    <span>
                      <span className="font-medium">{skill.technology.name}</span> · {label(LEVELS, skill.level)}
                      {skill.years_experience ? ` · ${skill.years_experience} an(s)` : ""}
                    </span>
                    <Badge tone={skill.is_verified ? "brand" : "neutral"}>{skill.verification_label}</Badge>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">Aucune compétence renseignée.</p>
            )}
            {data.links && data.links.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-3 text-sm">
                {data.links.map((link) => (
                  <a key={link.id} href={link.url} target="_blank" rel="noopener noreferrer nofollow" className="text-brand-300 underline">
                    {link.platform.toLowerCase()}
                  </a>
                ))}
              </div>
            )}
          </Card>

          {reputation.data && (
            <Card>
              <h2 className="font-semibold">Contributions · {reputation.data.score} points</h2>
              <p className="mb-3 text-xs text-muted">{reputation.data.explanation}</p>
              <div className="flex flex-wrap gap-2">
                {reputation.data.achievements.map((achievement) => (
                  <Badge key={achievement.code} tone="accent">🏅 {achievement.name}</Badge>
                ))}
              </div>
              {reputation.data.breakdown.length > 0 && (
                <ul className="mt-3 space-y-1 text-sm">
                  {reputation.data.breakdown.map((row) => (
                    <li key={row.event_type}>{row.label} : {row.count} ({row.points} pts)</li>
                  ))}
                </ul>
              )}
            </Card>
          )}

          <section>
            <h2 className="mb-3 font-semibold">Projets</h2>
            {projects.data?.count === 0 && <p className="text-sm text-muted">Aucun projet public.</p>}
            <div className="grid gap-3 sm:grid-cols-2">
              {projects.data?.results.map((project) => <ProjectCard key={project.id} project={project} />)}
            </div>
            <p className="mt-3 text-sm"><Link href="/projets" className="text-brand-300 underline">Découvrir d'autres projets</Link></p>
          </section>
        </>
      )}
    </div>
  );
}
