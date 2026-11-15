"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";

const NAV = [
  { href: "/fil", label: "Fil" },
  { href: "/questions", label: "Questions" },
  { href: "/developpeurs", label: "Développeurs" },
  { href: "/projets", label: "Projets" },
];

const POLL_MS = 60_000;

export function Header() {
  const { user, status, isModerator, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);

  // Pas de temps réel côté API : le compteur est rafraîchi périodiquement.
  useEffect(() => {
    if (status !== "authenticated") return;
    let active = true;
    const load = () =>
      api<{ unread: number }>("/notifications/unread-count/")
        .then((body) => active && setUnread(body.unread))
        .catch(() => undefined);
    load();
    const timer = window.setInterval(load, POLL_MS);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [status, pathname]);

  const links = isModerator ? [...NAV, { href: "/moderation", label: "Modération" }] : NAV;

  async function handleLogout() {
    await logout();
    router.push("/");
  }

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="text-lg font-bold text-brand-800">
          AfriDev<span className="text-accent-500">.</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Navigation principale">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={pathname.startsWith(link.href) ? "page" : undefined}
              className="rounded-lg px-3 py-2 text-sm text-muted hover:bg-stone-100 aria-[current=page]:font-semibold aria-[current=page]:text-brand-800"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {status === "authenticated" && user ? (
            <>
              <Link href="/publier" className="hidden rounded-lg bg-brand-700 px-3 py-2 text-sm font-medium text-white hover:bg-brand-800 sm:inline-flex">
                Publier
              </Link>
              <Link href="/notifications" className="relative rounded-lg px-2 py-2 text-sm text-muted hover:bg-stone-100" aria-label={`Notifications (${unread} non lues)`}>
                <span aria-hidden>🔔</span>
                {unread > 0 && (
                  <span className="absolute -right-0.5 -top-0.5 min-w-5 rounded-full bg-accent-500 px-1 text-center text-[11px] font-semibold text-white">
                    {unread > 99 ? "99+" : unread}
                  </span>
                )}
              </Link>
              <Link href={`/membres/${user.username}`} className="hidden text-sm font-medium hover:underline sm:inline">
                {user.username}
              </Link>
            </>
          ) : status === "anonymous" ? (
            <>
              <Link href="/connexion" className="rounded-lg px-3 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50">
                Connexion
              </Link>
              <Link href="/inscription" className="hidden rounded-lg bg-brand-700 px-3 py-2 text-sm font-medium text-white sm:inline-flex">
                Créer un compte
              </Link>
            </>
          ) : null}
          <button type="button" className="rounded-lg p-2 md:hidden" aria-expanded={open} aria-controls="mobile-nav" aria-label="Menu" onClick={() => setOpen((value) => !value)}>
            <span aria-hidden>☰</span>
          </button>
        </div>
      </div>

      {open && (
        <nav id="mobile-nav" className="border-t border-line px-4 pb-4 md:hidden" aria-label="Navigation mobile" onClick={() => setOpen(false)}>
          {links.map((link) => (
            <Link key={link.href} href={link.href} className="block rounded-lg px-3 py-3 text-sm hover:bg-stone-100">
              {link.label}
            </Link>
          ))}
          {status === "authenticated" && user ? (
            <>
              <Link href="/publier" className="block rounded-lg px-3 py-3 text-sm font-medium text-brand-700">Publier</Link>
              <Link href="/parametres" className="block rounded-lg px-3 py-3 text-sm">Mon profil</Link>
              <button type="button" onClick={handleLogout} className="block w-full rounded-lg px-3 py-3 text-left text-sm text-red-700">
                Se déconnecter
              </button>
            </>
          ) : (
            <Link href="/inscription" className="block rounded-lg px-3 py-3 text-sm font-medium text-brand-700">Créer un compte</Link>
          )}
        </nav>
      )}

      {status === "authenticated" && (
        <div className="mx-auto hidden max-w-5xl justify-end gap-4 px-4 pb-2 text-xs text-muted md:flex">
          <Link href="/parametres" className="hover:underline">Mon profil</Link>
          <button type="button" onClick={handleLogout} className="hover:underline">Se déconnecter</button>
        </div>
      )}
    </header>
  );
}
