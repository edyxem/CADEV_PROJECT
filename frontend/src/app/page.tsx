"use client";

import { motion } from "motion/react";
import Link from "next/link";

import { PostCard } from "@/components/community/PostCard";
import { AfricaNetwork } from "@/components/motion/AfricaNetwork";
import { Magnetic, Marquee, SpotlightCard } from "@/components/motion/Interactive";
import { Journey } from "@/components/motion/Journey";
import { CountUp, KineticHeadline, RotatingWord } from "@/components/motion/Kinetic";
import { Reveal } from "@/components/motion/Reveal";
import { ProjectCard } from "@/components/projects/ProjectCard";
import { ButtonLink } from "@/components/ui/Button";
import { Loading } from "@/components/ui/Feedback";
import type { Paginated, Post, Project, Ref } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useApi } from "@/lib/useApi";

const EASE = [0.22, 1, 0.36, 1] as const;

const FEATURES = [
  {
    title: "Questions & réponses",
    text: "Posez une question précise, recevez des réponses votées et acceptez celle qui vous débloque.",
    span: "md:col-span-2",
  },
  {
    title: "Annuaire de talents",
    text: "Filtrez par technologie, pays, disponibilité et niveau déclaré.",
    span: "",
  },
  {
    title: "Projets & équipes",
    text: "Publiez un appel à collaboration, acceptez des demandes et suivez vos tâches en Kanban.",
    span: "",
  },
  {
    title: "Confiance & modération",
    text: "Signalements, modération journalisée et compétences déclarées clairement distinguées des preuves.",
    span: "md:col-span-2",
  },
];

function StatPill({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div className="border-l border-line px-4 py-1">
      <p className="font-display text-2xl font-bold sm:text-3xl">
        {value === undefined ? <span className="skeleton inline-block h-7 w-12 align-middle" /> : <CountUp value={value} />}
      </p>
      <p className="text-xs text-muted">{label}</p>
    </div>
  );
}

function FloatingCard({ className, delay, children }: { className: string; delay: number; children: React.ReactNode }) {
  return (
    <motion.div
      className={`glass absolute z-10 hidden max-w-[15rem] rounded-2xl border border-line p-3 text-xs shadow-lg lg:block ${className}`}
      initial={{ opacity: 0, y: 20, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.8, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

export default function HomePage() {
  const { status } = useAuth();
  const posts = useApi<Paginated<Post>>("/posts/", { page_size: 4 });
  const projects = useApi<Paginated<Project>>("/projects/", { page_size: 2, recruiting: "true" });
  const members = useApi<Paginated<unknown>>("/profiles/", { page_size: 1 });
  const technologies = useApi<Paginated<Ref>>("/technologies/", { page_size: 60 });
  const latestQuestion = posts.data?.results.find((post) => post.type === "QUESTION");
  const latestProject = projects.data?.results[0];
  const techNames = technologies.data?.results.map((technology) => technology.name) ?? [];
  const half = Math.ceil(techNames.length / 2);

  return (
    <div className="space-y-28">
      {/* ── Héro ─────────────────────────────────────────────────────────── */}
      <section className="relative grid items-center gap-10 lg:grid-cols-[1.1fr_1fr]">
        <div className="grid-fade pointer-events-none absolute -inset-x-20 -top-20 bottom-0 -z-10" aria-hidden />
        <div>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-5 inline-flex items-center gap-2 rounded-full border border-line bg-panel/70 px-3 py-1 text-xs text-muted"
          >
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-400 opacity-70" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-brand-400" />
            </span>
            La communauté tech africaine, en direct
          </motion.p>

          <h1 className="font-display text-[2.6rem] font-bold leading-[1.02] tracking-tight sm:text-6xl lg:text-7xl">
            <KineticHeadline text="L'espace où la tech africaine" />
            <br />
            <span className="text-gradient">
              <RotatingWord words={["échange.", "se rencontre.", "construit."]} />
            </span>
          </h1>

          <motion.p
            className="mt-6 max-w-xl text-base text-muted sm:text-lg"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.7, ease: EASE }}
          >
            Trouvez des réponses, des pairs et des collaborateurs pour passer de la discussion à la réalisation de projets concrets.
          </motion.p>

          <motion.div className="mt-8 flex flex-wrap items-center gap-3" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.75, duration: 0.7, ease: EASE }}>
            <Magnetic>
              {status === "authenticated" ? (
                <ButtonLink href="/publier" className="px-6 py-3.5 text-base">Publier maintenant →</ButtonLink>
              ) : (
                <ButtonLink href="/inscription" className="px-6 py-3.5 text-base">Rejoindre la communauté →</ButtonLink>
              )}
            </Magnetic>
            <Magnetic strength={0.25}>
              <ButtonLink href="/fil" variant="onDark" className="px-6 py-3.5 text-base">Explorer le fil</ButtonLink>
            </Magnetic>
          </motion.div>

          <motion.div className="mt-10 grid max-w-md grid-cols-3 gap-3" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.95 }}>
            <StatPill label="développeurs" value={members.data?.count} />
            <StatPill label="publications" value={posts.data?.count} />
            <StatPill label="projets ouverts" value={projects.data?.count} />
          </motion.div>
        </div>

        <div className="relative">
          <motion.div
            className="relative mx-auto aspect-[100/104] w-full max-w-[34rem]"
            initial={{ opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1.1, ease: EASE }}
          >
            <AfricaNetwork className="h-full w-full drop-" />
          </motion.div>

          {latestQuestion && (
            <FloatingCard className="-left-10 bottom-16" delay={1.6}>
              <p className="mb-1 font-semibold text-ocre-300">Nouvelle question</p>
              <Link href={`/publications/${latestQuestion.id}`} className="line-clamp-2 text-ink hover:underline">{latestQuestion.title}</Link>
              <p className="mt-1 text-muted">{latestQuestion.answer_count} réponse(s) · {latestQuestion.author.display_name}</p>
            </FloatingCard>
          )}
          {latestProject && (
            <FloatingCard className="-right-6 top-0" delay={2}>
              <p className="mb-1 font-semibold text-brand-300">Projet en recrutement</p>
              <Link href={`/projets/${latestProject.slug}`} className="font-medium text-ink hover:underline">{latestProject.name}</Link>
              <p className="mt-1 text-muted">{latestProject.open_role_count} rôle(s) ouvert(s) · {latestProject.member_count} membre(s)</p>
            </FloatingCard>
          )}
        </div>
      </section>

      {/* ── Technologies ─────────────────────────────────────────────────── */}
      {techNames.length > 0 && (
        <section aria-label="Technologies de la communauté" className="-mx-4 space-y-3">
          <Marquee duration={55}>
            {techNames.slice(0, half).map((name) => (
              <span key={name} className="whitespace-nowrap rounded-full border border-line bg-panel px-4 py-2 text-sm text-muted">{name}</span>
            ))}
          </Marquee>
          <Marquee reverse duration={60}>
            {techNames.slice(half).map((name) => (
              <span key={name} className="whitespace-nowrap rounded-full border border-line bg-panel px-4 py-2 text-sm text-muted">{name}</span>
            ))}
          </Marquee>
        </section>
      )}

      {/* ── Fonctionnalités ──────────────────────────────────────────────── */}
      <section>
        <Reveal>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-ocre-400">Une plateforme, trois élans</p>
          <h2 className="mt-3 max-w-2xl font-display text-3xl font-bold sm:text-5xl">
            Échanger, se connecter, <span className="text-gradient">construire</span>.
          </h2>
        </Reveal>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {FEATURES.map((feature, index) => (
            <Reveal key={feature.title} delay={index * 0.08} className={feature.span}>
              <SpotlightCard className="h-full p-6 sm:p-8">
                <p className="mb-8 font-mono text-xs tabular-nums text-muted" aria-hidden>
                  {String(index + 1).padStart(2, "0")}
                </p>
                <h3 className="font-display text-xl font-semibold">{feature.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{feature.text}</p>
              </SpotlightCard>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── Parcours ─────────────────────────────────────────────────────── */}
      <section className="grid gap-12 lg:grid-cols-2">
        <div className="lg:sticky lg:top-32 lg:self-start">
          <Reveal>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-ocre-400">Le parcours</p>
            <h2 className="mt-3 font-display text-3xl font-bold sm:text-5xl">
              De la discussion à la <span className="text-gradient">réalisation</span>.
            </h2>
            <p className="mt-4 max-w-md text-muted">
              Une discussion utile reste précieuse même sans projet. Mais quand les bonnes personnes se rencontrent, la plateforme les aide à aller plus loin.
            </p>
          </Reveal>
        </div>
        <Journey />
      </section>

      {/* ── Activité récente ─────────────────────────────────────────────── */}
      <section className="grid gap-10 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <Reveal className="mb-5 flex items-end justify-between">
            <h2 className="font-display text-2xl font-bold">Discussions récentes</h2>
            <Link href="/fil" className="text-sm text-brand-300 hover:underline">Tout le fil →</Link>
          </Reveal>
          {posts.loading && !posts.data && <Loading rows={2} />}
          <div className="space-y-3">
            {posts.data?.results.slice(0, 3).map((post, index) => (
              <Reveal key={post.id} delay={index * 0.08}>
                <PostCard post={post} />
              </Reveal>
            ))}
          </div>
        </div>
        <div>
          <Reveal className="mb-5 flex items-end justify-between">
            <h2 className="font-display text-2xl font-bold">Ils recrutent</h2>
            <Link href="/projets" className="text-sm text-brand-300 hover:underline">Tous les projets →</Link>
          </Reveal>
          <div className="space-y-3">
            {projects.data?.results.map((project, index) => (
              <Reveal key={project.id} delay={index * 0.1}>
                <ProjectCard project={project} />
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Appel final ──────────────────────────────────────────────────── */}
      <Reveal>
        <section className="relative overflow-hidden rounded-2xl border border-line bg-panel-2 px-6 py-16 text-center sm:px-16">
          <h2 className="relative mx-auto max-w-2xl font-display text-3xl font-bold sm:text-5xl">
            Votre prochaine collaboration commence par une question.
          </h2>
          <p className="relative mx-auto mt-4 max-w-xl text-muted">
            Rejoignez des développeurs de tout le continent, partagez ce que vous savez et construisez ce qui manque.
          </p>
          <div className="relative mt-8 flex flex-wrap justify-center gap-3">
            <Magnetic>
              <ButtonLink href={status === "authenticated" ? "/projets/nouveau" : "/inscription"} className="px-7 py-3.5 text-base">
                {status === "authenticated" ? "Lancer un projet" : "Créer mon compte"}
              </ButtonLink>
            </Magnetic>
            <ButtonLink href="/developpeurs" variant="onDark" className="px-7 py-3.5 text-base">Découvrir les talents</ButtonLink>
          </div>
        </section>
      </Reveal>
    </div>
  );
}
