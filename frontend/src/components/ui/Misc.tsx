import Link from "next/link";
import type { ReactNode } from "react";

import type { Author } from "@/lib/api/types";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-line bg-white p-4 shadow-sm sm:p-5 ${className}`}>{children}</div>;
}

const TONES = {
  neutral: "bg-stone-100 text-stone-700",
  brand: "bg-brand-100 text-brand-800",
  accent: "bg-amber-100 text-amber-800",
  danger: "bg-red-100 text-red-800",
};

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: keyof typeof TONES }) {
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>{children}</span>;
}

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
      <img src={author.avatar} alt="" width={size} height={size} className="rounded-full object-cover" style={{ width: size, height: size }} />
    );
  }
  return (
    <span
      aria-hidden
      className="inline-flex items-center justify-center rounded-full bg-brand-100 font-semibold text-brand-800"
      style={{ width: size, height: size, fontSize: size / 2.6 }}
    >
      {initials}
    </span>
  );
}

export function AuthorLine({ author, children }: { author: Author; children?: ReactNode }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted">
      <Avatar author={author} size={28} />
      <Link href={`/membres/${author.username}`} className="font-medium text-ink hover:underline">
        {author.display_name}
      </Link>
      {children}
    </div>
  );
}

/** Affiche un HTML déjà assaini côté serveur par une liste blanche (nh3) : aucune balise script ni attribut d'événement. */
export function RichText({ html }: { html: string }) {
  return <div className="rich-text text-[15px] leading-relaxed" dangerouslySetInnerHTML={{ __html: html }} />;
}

export function PageTitle({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
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
  return (
    <nav aria-label="Pagination" className="mt-6 flex items-center justify-between text-sm">
      <button type="button" disabled={page <= 1} onClick={() => onChange(page - 1)} className="rounded-lg border border-line bg-white px-3 py-1.5 disabled:opacity-40">
        Précédent
      </button>
      <span className="text-muted">
        Page {page} sur {pages}
      </span>
      <button type="button" disabled={page >= pages} onClick={() => onChange(page + 1)} className="rounded-lg border border-line bg-white px-3 py-1.5 disabled:opacity-40">
        Suivant
      </button>
    </nav>
  );
}
