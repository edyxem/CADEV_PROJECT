"use client";

import { motion } from "motion/react";
import Link from "next/link";
import type { ReactNode } from "react";

import type { ApiError } from "@/lib/api/client";

type Kind = "info" | "success" | "error";

const KINDS: Record<Kind, string> = {
  info: "border-sky-400/25 bg-sky-400/10 text-sky-100",
  success: "border-brand-400/30 bg-brand-500/10 text-brand-200",
  error: "border-rose-400/30 bg-rose-500/10 text-rose-100",
};

export function Alert({ kind = "info", children }: { kind?: Kind; children: ReactNode }) {
  return (
    <motion.div
      role={kind === "error" ? "alert" : "status"}
      initial={{ opacity: 0, y: -6, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className={`mb-4 rounded-xl border px-4 py-3 text-sm ${KINDS[kind]}`}
    >
      {children}
    </motion.div>
  );
}

/** Squelettes de chargement : la page garde sa forme pendant l'attente. */
export function Loading({ label = "Chargement…", rows = 3 }: { label?: string; rows?: number }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3 py-2">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="rounded-2xl border border-line bg-panel p-5" style={{ opacity: 1 - index * 0.2 }}>
          <div className="skeleton mb-3 h-4 w-24" />
          <div className="skeleton mb-2 h-5 w-3/4" />
          <div className="skeleton h-4 w-1/2" />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="rounded-2xl border border-dashed border-line bg-panel/60 px-6 py-12 text-center"
    >
      <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-brand-500/10 text-xl text-brand-300" aria-hidden>
        ✦
      </div>
      <p className="font-display text-lg font-semibold">{title}</p>
      {children && <div className="mt-2 text-sm text-muted">{children}</div>}
    </motion.div>
  );
}

/** Message adapté au statut de l'erreur (§9.5 : permission, contenu indisponible, session…). */
export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  if (error.status === 404) {
    return <EmptyState title="Contenu indisponible">Il a peut-être été supprimé, masqué ou n'est pas public.</EmptyState>;
  }
  if (error.status === 401) {
    return (
      <EmptyState title="Connexion requise">
        <Link href="/connexion" className="text-brand-300 underline">
          Se connecter
        </Link>{" "}
        pour accéder à cette page.
      </EmptyState>
    );
  }
  if (error.status === 403) {
    return <EmptyState title="Accès non autorisé">{error.message}</EmptyState>;
  }
  return (
    <Alert kind="error">
      {error.message}{" "}
      {onRetry && (
        <button type="button" onClick={onRetry} className="font-semibold underline">
          Réessayer
        </button>
      )}
    </Alert>
  );
}
