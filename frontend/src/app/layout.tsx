import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";

import { Header } from "@/components/layout/Header";
import { MotionProvider } from "@/components/motion/Providers";
import { AuthProvider } from "@/lib/auth/AuthProvider";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const grotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-grotesk", display: "swap" });

export const metadata: Metadata = {
  title: { default: "AfriDev Community", template: "%s · AfriDev Community" },
  description:
    "Échanger, se connecter, construire : l'espace communautaire des développeurs africains.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#070f0c" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${inter.variable} ${grotesk.variable} overflow-x-clip`}>
      <body className="min-h-screen overflow-x-clip antialiased">
        {/* Halo d'ambiance commun à toutes les pages. */}
        <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
          <div className="absolute -left-40 -top-40 h-[32rem] w-[32rem] animate-aurora rounded-full bg-brand-500/10 blur-3xl" />
          <div className="absolute -right-40 top-1/3 h-[28rem] w-[28rem] animate-aurora rounded-full bg-ocre-500/[0.06] blur-3xl [animation-delay:-6s]" />
        </div>
        <MotionProvider>
          <AuthProvider>
            <a href="#contenu" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-panel focus:px-3 focus:py-2">
              Aller au contenu
            </a>
            <Header />
            <main id="contenu" className="mx-auto max-w-6xl px-4 pb-16 pt-24 sm:pt-28">
              {children}
            </main>
            <footer className="border-t border-line">
              <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-xs text-muted sm:flex-row sm:items-center sm:justify-between">
                <p>
                  <span className="font-display text-sm font-semibold text-ink">AfriDev</span>
                  <span className="text-ocre-400">.</span> Échanger · Se connecter · Construire
                </p>
                <p>CADEV 2026 — données de démonstration fictives.</p>
              </div>
            </footer>
          </AuthProvider>
        </MotionProvider>
      </body>
    </html>
  );
}
