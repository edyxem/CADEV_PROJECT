"use client";

import { MotionConfig } from "motion/react";
import type { ReactNode } from "react";

/** Toutes les animations Motion suivent le réglage système « réduire les animations ». */
export function MotionProvider({ children }: { children: ReactNode }) {
  return (
    <MotionConfig reducedMotion="user" transition={{ type: "spring", stiffness: 260, damping: 28 }}>
      {children}
    </MotionConfig>
  );
}
