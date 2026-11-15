"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";

import { AfricaNetwork } from "@/components/motion/AfricaNetwork";
import { KineticHeadline } from "@/components/motion/Kinetic";

const POINTS = [
  "Des réponses techniques adaptées à votre contexte",
  "Des pairs qui utilisent les mêmes technologies",
  "Des équipes pour passer de l'idée au projet",
];

/** Mise en page des écrans d'authentification : panneau de marque animé + formulaire. */
export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="grid overflow-hidden rounded-[2rem] border border-line bg-panel lg:grid-cols-2">
      <div className="grain relative hidden overflow-hidden bg-gradient-to-br from-brand-500/15 via-night to-ocre-500/10 p-10 lg:block">
        <div className="absolute -bottom-24 -right-24 w-[26rem] opacity-70" aria-hidden>
          <AfricaNetwork />
        </div>
        <div className="relative">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-ocre-400">AfriDev Community</p>
          <h2 className="mt-4 max-w-sm font-display text-4xl font-bold leading-tight">
            <KineticHeadline text="Échanger. Se connecter. Construire." />
          </h2>
          <ul className="mt-8 space-y-3">
            {POINTS.map((point, index) => (
              <motion.li
                key={point}
                className="flex items-center gap-3 text-sm text-ink/85"
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 + index * 0.12 }}
              >
                <span className="grid h-6 w-6 place-items-center rounded-full bg-brand-500/15 text-xs text-brand-300" aria-hidden>✓</span>
                {point}
              </motion.li>
            ))}
          </ul>
        </div>
      </div>
      <div className="p-6 sm:p-10">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <h1 className="font-display text-3xl font-bold">{title}</h1>
          <p className="mb-8 mt-2 text-sm text-muted">{subtitle}</p>
          {children}
        </motion.div>
      </div>
    </div>
  );
}
