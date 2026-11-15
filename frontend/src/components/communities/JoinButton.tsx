"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { useState } from "react";

import { api } from "@/lib/api/client";
import type { CommunityItem } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";

/** Rejoindre / quitter une communauté, avec compteur de membres mis à jour immédiatement. */
export function JoinButton({ community, onChange }: { community: CommunityItem; onChange?: (community: CommunityItem) => void }) {
  const { status } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const member = community.my_role !== null;

  if (status !== "authenticated") {
    return (
      <Link href={`/connexion?next=/communautes/${community.slug}`} className="relative z-10 text-sm text-brand-300 underline">
        Se connecter pour rejoindre
      </Link>
    );
  }

  async function toggle() {
    setBusy(true);
    setError("");
    try {
      await api(`/communities/${community.slug}/${member ? "leave" : "join"}/`, { method: "POST" });
      onChange?.({ ...community, my_role: member ? null : "MEMBER", member_count: community.member_count + (member ? -1 : 1) });
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative z-10">
      <motion.button
        type="button"
        whileTap={{ scale: 0.95 }}
        disabled={busy}
        onClick={toggle}
        className={`rounded-xl px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-50 ${member ? "border border-line text-muted hover:border-rose-400/50 hover:text-rose-700" : "btn-primary"}`}
      >
        {member ? (community.my_role === "LEADER" ? "Responsable · quitter" : "Membre · quitter") : "Rejoindre"}
      </motion.button>
      {error && <p className="mt-1 text-xs text-rose-700">{error}</p>}
    </div>
  );
}
