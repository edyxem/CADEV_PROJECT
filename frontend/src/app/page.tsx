"use client";

import Link from "next/link";

import { PostCard } from "@/components/community/PostCard";
import { ButtonLink } from "@/components/ui/Button";
import { ErrorState, Loading } from "@/components/ui/Feedback";
import type { Paginated, Post } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useApi } from "@/lib/useApi";

const PILLARS = [
  { title: "Échanger", text: "Posez vos questions techniques, partagez vos retours d'expérience et vos tutoriels." },
  { title: "Se connecter", text: "Trouvez des développeurs par technologie, pays ou disponibilité." },
  { title: "Construire", text: "Lancez un projet, constituez une équipe et suivez vos tâches." },
];

export default function HomePage() {
  const { status } = useAuth();
  const latest = useApi<Paginated<Post>>("/posts/", { page_size: 5 });

  return (
    <div className="space-y-10">
      <section className="rounded-2xl bg-brand-800 px-6 py-10 text-white sm:px-10">
        <h1 className="max-w-2xl text-3xl font-bold leading-tight sm:text-4xl">
          L'espace où la communauté tech africaine échange, se rencontre et construit.
        </h1>
        <p className="mt-4 max-w-xl text-brand-100">
          Trouvez des réponses, des pairs et des collaborateurs pour passer de la discussion à la réalisation de projets concrets.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          {status === "authenticated" ? (
            <ButtonLink href="/publier" variant="light">Publier</ButtonLink>
          ) : (
            <ButtonLink href="/inscription" variant="light">Créer un compte</ButtonLink>
          )}
          <ButtonLink href="/fil" variant="onDark">Parcourir le fil</ButtonLink>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {PILLARS.map((pillar) => (
          <div key={pillar.title} className="rounded-xl border border-line bg-white p-5">
            <h2 className="font-semibold text-brand-800">{pillar.title}</h2>
            <p className="mt-2 text-sm text-muted">{pillar.text}</p>
          </div>
        ))}
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Discussions récentes</h2>
          <Link href="/fil" className="text-sm text-brand-700 hover:underline">Tout voir</Link>
        </div>
        {latest.loading && <Loading />}
        {latest.error && <ErrorState error={latest.error} onRetry={latest.reload} />}
        <div className="space-y-3">
          {latest.data?.results.map((post) => <PostCard key={post.id} post={post} />)}
        </div>
      </section>
    </div>
  );
}
