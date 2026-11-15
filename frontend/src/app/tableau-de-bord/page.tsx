"use client";

import Link from "next/link";
import { useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { CountUp } from "@/components/motion/Kinetic";
import { SpotlightCard } from "@/components/motion/Interactive";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/Reveal";
import { ProfileCard } from "@/components/profiles/ProfileCard";
import { ProjectCard } from "@/components/projects/ProjectCard";
import { Button } from "@/components/ui/Button";
import { Alert, ErrorState, Loading } from "@/components/ui/Feedback";
import { PageTitle } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { Dashboard, Paginated, Profile, Project } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useApi } from "@/lib/useApi";

const SHORTCUTS = [
  { href: "/publier", title: "Publier", text: "Poser une question ou partager une expérience." },
  { href: "/projets/nouveau", title: "Lancer un projet", text: "Constituer une équipe autour d'une idée." },
  { href: "/opportunites", title: "Opportunités", text: "Emplois, stages, bourses et hackathons." },
  { href: "/evenements", title: "Événements", text: "Meetups, ateliers et webinaires à venir." },
  { href: "/communautes", title: "Communautés", text: "Rejoindre son pays, sa ville ou sa techno." },
  { href: "/mentorat", title: "Mentorat", text: "Être accompagné par un développeur confirmé." },
];

function Stat({ label, value, href }: { label: string; value: number; href?: string }) {
  const content = (
    <SpotlightCard className="h-full p-4">
      <p className="font-display text-3xl font-bold">
        <CountUp value={value} />
      </p>
      <p className="mt-1 text-xs text-muted">{label}</p>
    </SpotlightCard>
  );
  return href ? (
    <Link href={href} className="block h-full">
      {content}
    </Link>
  ) : (
    content
  );
}

function EmailBanner() {
  const [state, setState] = useState<"idle" | "sent" | "error">("idle");
  const [message, setMessage] = useState("");

  async function resend() {
    try {
      await api("/auth/email/verify/resend/", { method: "POST" });
      setState("sent");
    } catch (caught) {
      setMessage((caught as ApiError).message);
      setState("error");
    }
  }

  if (state === "sent") return <Alert kind="success">Un nouveau lien de vérification vient d&apos;être envoyé.</Alert>;
  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-ocre-400/30 bg-ocre-500/10 px-4 py-3 text-sm">
      <p>
        <span className="font-semibold text-ocre-300">Adresse e-mail non vérifiée.</span>{" "}
        {state === "error" ? message : "Vérifiez-la pour recevoir les notifications par e-mail."}
      </p>
      <Button variant="secondary" onClick={resend} className="px-3 py-1.5 text-xs">
        Renvoyer le lien
      </Button>
    </div>
  );
}

function DashboardContent() {
  const { user } = useAuth();
  const dashboard = useApi<Dashboard>("/me/dashboard/");
  const developers = useApi<Paginated<Profile>>("/recommendations/developers/", { page_size: 4 });
  const projects = useApi<Paginated<Project>>("/recommendations/projects/", { page_size: 4 });

  if (dashboard.error) return <ErrorState error={dashboard.error} onRetry={dashboard.reload} />;
  const data = dashboard.data;

  return (
    <div>
      <PageTitle eyebrow="Mon espace" title={`Bonjour ${user?.first_name || user?.username || ""} 👋`} subtitle="Votre activité sur AfriDev Community et des suggestions choisies pour vous." />
      {user && !user.email_verified && <EmailBanner />}

      {!data ? (
        <Loading rows={2} />
      ) : (
        <Stagger className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StaggerItem>
            <Stat label="Points de réputation" value={data.reputation} href={user ? `/membres/${user.username}` : undefined} />
          </StaggerItem>
          <StaggerItem>
            <Stat label="Publications" value={data.posts} />
          </StaggerItem>
          <StaggerItem>
            <Stat label="Réponses (dont acceptées)" value={data.answers} />
          </StaggerItem>
          <StaggerItem>
            <Stat label="Notifications non lues" value={data.unread_notifications} href="/notifications" />
          </StaggerItem>
          <StaggerItem>
            <Stat label="Projets" value={data.projects} href="/projets" />
          </StaggerItem>
          <StaggerItem>
            <Stat label="Tâches ouvertes" value={data.open_tasks} />
          </StaggerItem>
          <StaggerItem>
            <Stat label="Demandes à examiner" value={data.join_requests_to_review} />
          </StaggerItem>
          <StaggerItem>
            <Stat label="Abonnés" value={data.followers} />
          </StaggerItem>
        </Stagger>
      )}

      <Reveal className="mt-10">
        <h2 className="mb-3 font-display text-xl font-semibold">Raccourcis</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {SHORTCUTS.map((shortcut) => (
            <Link key={shortcut.href} href={shortcut.href} className="group rounded-2xl border border-line bg-panel p-4 transition-colors hover:border-brand-400/40">
              <p className="font-semibold group-hover:text-brand-200">
                {shortcut.title} <span className="inline-block transition-transform group-hover:translate-x-1">→</span>
              </p>
              <p className="mt-1 text-sm text-muted">{shortcut.text}</p>
            </Link>
          ))}
        </div>
      </Reveal>

      <Reveal className="mt-10">
        <h2 className="mb-1 font-display text-xl font-semibold">Développeurs à rencontrer</h2>
        <p className="mb-3 text-sm text-muted">Suggestions fondées sur les technologies que vous partagez.</p>
        {developers.loading && !developers.data && <Loading rows={1} />}
        <div className="grid gap-3 sm:grid-cols-2">
          {developers.data?.results.map((profile) => <ProfileCard key={profile.username} profile={profile} />)}
        </div>
        {developers.data?.results.length === 0 && <p className="text-sm text-muted">Complétez vos compétences dans les paramètres pour recevoir des suggestions.</p>}
      </Reveal>

      <Reveal className="mt-10">
        <h2 className="mb-1 font-display text-xl font-semibold">Projets qui pourraient vous intéresser</h2>
        <p className="mb-3 text-sm text-muted">Projets ouverts dont les technologies correspondent à votre profil.</p>
        {projects.loading && !projects.data && <Loading rows={1} />}
        <div className="grid gap-3 sm:grid-cols-2">
          {projects.data?.results.map((project) => <ProjectCard key={project.id} project={project} />)}
        </div>
        {projects.data?.results.length === 0 && <p className="text-sm text-muted">Aucune suggestion pour le moment.</p>}
      </Reveal>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <RequireAuth>
      <DashboardContent />
    </RequireAuth>
  );
}
