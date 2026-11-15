"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Feedback";
import { Select, Textarea } from "@/components/ui/Field";
import { api, ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { REPORT_REASONS } from "@/lib/labels";

/** Vote utile : l'état final et le compteur viennent toujours de l'API. */
export function VoteButton({ path, voted, count, disabled }: { path: string; voted: boolean; count: number; disabled?: boolean }) {
  const { status } = useAuth();
  const [state, setState] = useState({ voted, count });
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function toggle() {
    setPending(true);
    setError(null);
    try {
      const result = await api<{ voted: boolean; vote_count: number }>(path, { method: "POST", body: { active: !state.voted } });
      setState({ voted: result.voted, count: result.vote_count });
    } catch (caught) {
      setError((caught as ApiError).message);
    } finally {
      setPending(false);
    }
  }

  return (
    <span className="inline-flex flex-col">
      <button
        type="button"
        onClick={toggle}
        disabled={status !== "authenticated" || disabled || pending}
        aria-pressed={state.voted}
        title={status === "authenticated" ? "Vote utile" : "Connectez-vous pour voter"}
        className="inline-flex items-center gap-1 rounded-lg border border-line bg-white px-2.5 py-1 text-sm aria-pressed:border-brand-600 aria-pressed:bg-brand-50 aria-pressed:text-brand-800 disabled:opacity-60"
      >
        ▲ <span>{state.count}</span>
      </button>
      {error && <span className="mt-1 text-xs text-red-700">{error}</span>}
    </span>
  );
}

const REASONS = Object.entries(REPORT_REASONS).map(([value, labelText]) => ({ value, label: labelText }));

/** Signalement d'un contenu ou d'un profil (§5.5). */
export function ReportButton({ targetType, targetId }: { targetType: string; targetId: string }) {
  const { status } = useAuth();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("SPAM");
  const [details, setDetails] = useState("");
  const [result, setResult] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [pending, setPending] = useState(false);

  if (status !== "authenticated") return null;

  async function submit() {
    setPending(true);
    try {
      await api("/reports/", { method: "POST", body: { target_type: targetType, target_id: targetId, reason, details } });
      setResult({ kind: "success", text: "Merci, le signalement a été transmis à la modération." });
      setOpen(false);
    } catch (caught) {
      const error = caught as ApiError;
      setResult({ kind: "error", text: error.field("details") ?? error.message });
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      {!open && (
        <button type="button" onClick={() => { setOpen(true); setResult(null); }} className="text-xs text-muted hover:text-red-700 hover:underline">
          Signaler
        </button>
      )}
      {result && <Alert kind={result.kind}>{result.text}</Alert>}
      {open && (
        <div className="mt-2 rounded-lg border border-line bg-stone-50 p-3">
          <Select label="Motif" options={REASONS} value={reason} onChange={(e) => setReason(e.target.value)} />
          <Textarea label="Précisions" value={details} onChange={(e) => setDetails(e.target.value)} rows={2} hint={reason === "OTHER" ? "Obligatoire pour « Autre motif »." : "Facultatif."} />
          <div className="flex gap-2">
            <Button type="button" variant="danger" loading={pending} onClick={submit}>Envoyer le signalement</Button>
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>Annuler</Button>
          </div>
        </div>
      )}
    </div>
  );
}
