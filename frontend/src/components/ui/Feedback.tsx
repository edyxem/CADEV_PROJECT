import Link from "next/link";
import type { ReactNode } from "react";

import type { ApiError } from "@/lib/api/client";

type Kind = "info" | "success" | "error";

const KINDS: Record<Kind, string> = {
  info: "border-sky-200 bg-sky-50 text-sky-900",
  success: "border-emerald-200 bg-emerald-50 text-emerald-900",
  error: "border-red-200 bg-red-50 text-red-900",
};

export function Alert({ kind = "info", children }: { kind?: Kind; children: ReactNode }) {
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`mb-4 rounded-lg border px-4 py-3 text-sm ${KINDS[kind]}`}>
      {children}
    </div>
  );
}

export function Loading({ label = "Chargement…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-8 text-sm text-muted" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" aria-hidden />
      {label}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-white px-6 py-10 text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="mt-2 text-sm text-muted">{children}</div>}
    </div>
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
        <Link href="/connexion" className="text-brand-700 underline">
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
        <button type="button" onClick={onRetry} className="font-medium underline">
          Réessayer
        </button>
      )}
    </Alert>
  );
}
