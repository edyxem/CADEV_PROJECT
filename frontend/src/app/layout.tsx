import type { Metadata, Viewport } from "next";

import { Header } from "@/components/layout/Header";
import { AuthProvider } from "@/lib/auth/AuthProvider";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "AfriDev Community", template: "%s · AfriDev Community" },
  description:
    "Échanger, se connecter, construire : l'espace communautaire des développeurs africains.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#065f46" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen antialiased">
        <AuthProvider>
          <a href="#contenu" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">
            Aller au contenu
          </a>
          <Header />
          <main id="contenu" className="mx-auto max-w-5xl px-4 py-6 sm:py-10">
            {children}
          </main>
          <footer className="border-t border-line py-6 text-center text-xs text-muted">
            AfriDev Community — CADEV 2026. Données de démonstration fictives.
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
