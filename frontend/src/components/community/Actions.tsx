"use client";

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { RollingNumber } from "@/components/motion/Kinetic";

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
      <motion.button
        type="button"
        onClick={toggle}
        disabled={status !== "authenticated" || disabled || pending}
        aria-pressed={state.voted}
        aria-label={state.voted ? "Retirer mon vote utile" : "Voter utile"}
        title={status === "authenticated" ? "Vote utile" : "Connectez-vous pour voter"}
        whileTap={{ scale: 0.88 }}
        className="relative inline-flex items-center gap-1.5 rounded-xl border border-line bg-panel px-3 py-1.5 text-sm transition-colors aria-pressed:border-brand-400/60 aria-pressed:bg-brand-50 aria-pressed:text-brand-200 disabled:opacity-60"
      >
        <motion.span
          aria-hidden
          animate={state.voted ? { y: [0, -5, 0], scale: [1, 1.35, 1] } : { y: 0, scale: 1 }}
          transition={{ duration: 0.45 }}
          className={state.voted ? "text-brand-300" : ""}
        >
          ▲
        </motion.span>
        <RollingNumber value={state.count} />
        <AnimatePresence>
          {state.voted && (
            <motion.span
              key="ring"
              aria-hidden
              className="pointer-events-none absolute inset-0 rounded-xl border border-brand-300"
              initial={{ opacity: 0.8, scale: 1 }}
              animate={{ opacity: 0, scale: 1.35 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.6 }}
            />
          )}
        </AnimatePresence>
      </motion.button>
      {error && <span className="mt-1 text-xs text-rose-700">{error}</span>}
    </span>
  );
}

const BURST = Array.from({ length: 8 }, (_, index) => (index / 8) * Math.PI * 2);

/** Favori : l'étoile se remplit avec une petite gerbe de particules. */
export function BookmarkButton({ active, onToggle }: { active: boolean; onToggle: () => void }) {
  return (
    <motion.button
      type="button"
      onClick={onToggle}
      aria-pressed={active}
      whileTap={{ scale: 0.9 }}
      className="relative inline-flex items-center gap-2 rounded-xl border border-line bg-panel-2 px-4 py-2.5 text-sm font-semibold transition-colors hover:bg-ink/5 aria-pressed:border-ocre-400/50 aria-pressed:text-ocre-300"
    >
      <span className="relative" aria-hidden>
        <motion.span className="inline-block" animate={active ? { rotate: [0, -20, 0], scale: [1, 1.4, 1] } : {}} transition={{ duration: 0.5 }}>
          {active ? "★" : "☆"}
        </motion.span>
        <AnimatePresence>
          {active &&
            BURST.map((angle) => (
              <motion.span
                key={angle}
                className="absolute left-1/2 top-1/2 h-1 w-1 rounded-full bg-ocre-300"
                initial={{ x: 0, y: 0, opacity: 1 }}
                animate={{ x: Math.cos(angle) * 16, y: Math.sin(angle) * 16, opacity: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.55, ease: "easeOut" }}
              />
            ))}
        </AnimatePresence>
      </span>
      {active ? "Enregistrée" : "Enregistrer"}
    </motion.button>
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
        <button type="button" onClick={() => { setOpen(true); setResult(null); }} className="text-xs text-muted hover:text-rose-700 hover:underline">
          Signaler
        </button>
      )}
      {result && <Alert kind={result.kind}>{result.text}</Alert>}
      {open && (
        <div className="mt-2 rounded-xl border border-line bg-panel-2 p-3">
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
