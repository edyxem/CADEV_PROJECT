"use client";

import { useEffect, useState } from "react";

import { AuthShell } from "@/components/layout/AuthShell";
import { ButtonLink } from "@/components/ui/Button";
import { Alert, Loading } from "@/components/ui/Feedback";
import { api, ApiError } from "@/lib/api/client";

type State = { kind: "pending" } | { kind: "ok" } | { kind: "error"; message: string };

// Un lien ne sert qu'une fois : la même requête est partagée si le composant est monté deux fois.
const inflight = new Map<string, Promise<unknown>>();

function confirmOnce(endpoint: string, payload: string): Promise<unknown> {
  const key = `${endpoint}|${payload}`;
  let request = inflight.get(key);
  if (!request) {
    request = api(endpoint, { method: "POST", body: JSON.parse(payload) });
    inflight.set(key, request);
  }
  return request;
}

/** Valide un lien reçu par e-mail (vérification d'adresse ou changement d'adresse). */
export function EmailConfirmation({ endpoint, body, title }: { endpoint: string; body: Record<string, string>; title: string }) {
  const [state, setState] = useState<State>({ kind: "pending" });
  const payload = JSON.stringify(body);

  useEffect(() => {
    let active = true;
    confirmOnce(endpoint, payload)
      .then(() => {
        if (active) setState({ kind: "ok" });
      })
      .catch((error: unknown) => {
        if (!active) return;
        const apiError = error instanceof ApiError ? error : null;
        const detail = apiError ? Object.values(apiError.errors)[0]?.[0] : undefined;
        setState({ kind: "error", message: String(detail ?? apiError?.message ?? "Ce lien est invalide ou a expiré.") });
      });
    return () => {
      active = false;
    };
  }, [endpoint, payload]);

  return (
    <AuthShell title={title} subtitle="Validation du lien reçu par e-mail.">
      {state.kind === "pending" && <Loading label="Vérification du lien…" rows={1} />}
      {state.kind === "ok" && <Alert kind="success">Votre adresse e-mail est confirmée. Merci !</Alert>}
      {state.kind === "error" && <Alert kind="error">{state.message}</Alert>}
      {state.kind !== "pending" && (
        <ButtonLink href="/tableau-de-bord" className="w-full">
          Aller au tableau de bord
        </ButtonLink>
      )}
    </AuthShell>
  );
}
