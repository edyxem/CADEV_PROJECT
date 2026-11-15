"use client";

import { motion, useScroll, useSpring, useTransform, type MotionValue } from "motion/react";
import { useRef } from "react";

const STEPS = [
  { title: "Discussion", text: "Une question technique, un retour d'expérience, un tutoriel." },
  { title: "Rencontre", text: "Des réponses utiles révèlent des profils complémentaires." },
  { title: "Équipe", text: "Un appel à collaboration réunit les bonnes compétences." },
  { title: "Projet", text: "Rôles, demandes, tâches : l'équipe s'organise." },
  { title: "Réalisation", text: "Le projet aboutit et rejoint les réalisations des membres." },
  { title: "Opportunité", text: "La réputation construite ouvre de nouvelles portes." },
];

function Step({ index, progress, title, text }: { index: number; progress: MotionValue<number>; title: string; text: string }) {
  const start = index / STEPS.length;
  const active = useTransform(progress, [start, start + 0.08], [0, 1]);
  const scale = useTransform(active, [0, 1], [0.6, 1]);
  const color = useTransform(active, [0, 1], ["#1e3029", "#fbbf24"]);
  const textOpacity = useTransform(active, [0, 1], [0.35, 1]);
  const x = useTransform(active, [0, 1], [-12, 0]);

  return (
    <li className="relative pb-10 pl-12 last:pb-0">
      <motion.span
        className="absolute left-[7px] top-1 h-[18px] w-[18px] rounded-full border-2 border-surface"
        style={{ scale, backgroundColor: color, boxShadow: "0 0 0 4px rgb(7 15 12)" }}
        aria-hidden
      />
      <motion.div style={{ opacity: textOpacity, x }}>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ocre-400">Étape {index + 1}</p>
        <h3 className="mt-1 text-2xl font-semibold">{title}</h3>
        <p className="mt-1 max-w-md text-sm text-muted">{text}</p>
      </motion.div>
    </li>
  );
}

/** Frise du parcours produit, dessinée au fil du défilement (§0.1). */
export function Journey() {
  const ref = useRef<HTMLOListElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 75%", "end 55%"] });
  const progress = useSpring(scrollYProgress, { stiffness: 120, damping: 24, restDelta: 0.001 });

  return (
    <ol ref={ref} className="relative">
      <span className="absolute bottom-2 left-4 top-2 w-px bg-line" aria-hidden />
      <motion.span
        className="absolute left-4 top-2 w-px origin-top bg-gradient-to-b from-brand-400 via-ocre-400 to-terra-400"
        style={{ scaleY: progress, bottom: 8 }}
        aria-hidden
      />
      {STEPS.map((step, index) => (
        <Step key={step.title} index={index} progress={progress} title={step.title} text={step.text} />
      ))}
    </ol>
  );
}
