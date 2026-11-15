import Link from "next/link";
import type { ReactNode } from "react";

import type { Author } from "@/lib/api/types";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-line bg-panel p-4 sm:p-6 ${className}`}>{children}</div>;
}

const TONES = {
  neutral: "border-line bg-panel-2 text-muted",
  brand: "border-brand-400/30 bg-brand-500/10 text-brand-200",
  accent: "border-ocre-400/30 bg-ocre-500/10 text-ocre-300",
  danger: "border-rose-400/30 bg-rose-500/10 text-rose-700",
};

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: keyof typeof TONES }) {
  return <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONES[tone]}`}>{children}</span>;
}

const AVATAR_GRADIENTS = ["bg-[#0b6e4f]", "bg-[#b06a08]", "bg-[#3f5873]", "bg-[#9a4421]", "bg-[#4b4f56]"];

export function Avatar({ author, size = 36 }: { author: Pick<Author, "display_name" | "avatar">; size?: number }) {
  const initials = author.display_name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  if (author.avatar) {
    return (
      // Les avatars sont réencodés et dimensionnés par l'API (WebP 512 px).
      // eslint-disable-next-line @next/next/no-img-element
      <img src={author.avatar} alt="" width={size} height={size} className="rounded-full object-cover ring-1 ring-line" style={{ width: size, height: size }} />
    );
  }
  const gradient = AVATAR_GRADIENTS[author.display_name.length % AVATAR_GRADIENTS.length];
  return (
    <span
      aria-hidden
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-display font-semibold text-white ${gradient}`}
      style={{ width: size, height: size, fontSize: size / 2.6 }}
    >
      {initials}
    </span>
  );
}

export function AuthorLine({ author, children }: { author: Author; children?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
      <Avatar author={author} size={28} />
      <Link href={`/membres/${author.username}`} className="font-medium text-ink hover:text-brand-300">
        {author.display_name}
      </Link>
      {children}
    </div>
  );
}

/** Affiche un HTML déjà assaini côté serveur par une liste blanche (nh3) : aucune balise script ni attribut d'événement. */
export function RichText({ html }: { html: string }) {
  return <div className="rich-text text-[15px] leading-relaxed text-ink/90" dangerouslySetInnerHTML={{ __html: html }} />;
}

export function PageTitle({ title, subtitle, action, eyebrow }: { title: string; subtitle?: string; action?: ReactNode; eyebrow?: string }) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && <p className="mb-2 text-xs font-semibold uppercase tracking-[0.22em] text-ocre-400">{eyebrow}</p>}
        <h1 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-sm text-muted sm:text-base">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Pagination({
  page,
  count,
  pageSize = 20,
  onChange,
}: {
  page: number;
  count: number;
  pageSize?: number;
  onChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (pages <= 1) return null;
  const goTo = (target: number) => {
    onChange(target);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  return (
    <nav aria-label="Pagination" className="mt-8 flex items-center justify-between text-sm">
      <button type="button" disabled={page <= 1} onClick={() => goTo(page - 1)} className="rounded-xl border border-line bg-panel px-4 py-2 transition-colors hover:bg-ink/5 disabled:opacity-40">
        ← Précédent
      </button>
      <span className="text-muted">
        Page <span className="font-semibold text-ink">{page}</span> sur {pages}
      </span>
      <button type="button" disabled={page >= pages} onClick={() => goTo(page + 1)} className="rounded-xl border border-line bg-panel px-4 py-2 transition-colors hover:bg-ink/5 disabled:opacity-40">
        Suivant →
      </button>
    </nav>
  );
}
