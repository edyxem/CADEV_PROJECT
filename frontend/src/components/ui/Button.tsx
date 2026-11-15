"use client";

import { motion } from "motion/react";
import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "light" | "onDark";

const VARIANTS: Record<Variant, string> = {
  primary: "btn-primary disabled:opacity-50",
  secondary: "border border-line bg-white text-ink hover:border-ink/30 hover:bg-panel-2 disabled:opacity-50",
  ghost: "text-brand-300 hover:bg-ink/5 disabled:opacity-50",
  danger: "border border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100 disabled:opacity-50",
  light: "bg-ink text-white hover:bg-ink/85",
  onDark: "border border-line text-ink hover:bg-ink/5",
};

const BASE =
  "relative inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed";

interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onAnimationStart" | "onDrag" | "onDragStart" | "onDragEnd"> {
  variant?: Variant;
  loading?: boolean;
}

export function Button({ variant = "primary", loading = false, className = "", children, disabled, ...props }: ButtonProps) {
  return (
    <motion.button
      {...props}
      whileHover={disabled || loading ? undefined : { y: -1 }}
      whileTap={disabled || loading ? undefined : { scale: 0.97 }}
      disabled={disabled || loading}
      aria-busy={loading}
      className={`${BASE} ${VARIANTS[variant]} ${className}`}
    >
      {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />}
      {children}
    </motion.button>
  );
}

export function ButtonLink({
  href,
  variant = "primary",
  className = "",
  children,
}: {
  href: string;
  variant?: Variant;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link href={href} className={`${BASE} ${VARIANTS[variant]} transition-transform hover:-translate-y-0.5 active:scale-[0.98] ${className}`}>
      {children}
    </Link>
  );
}
