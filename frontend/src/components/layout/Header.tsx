"use client";

import { AnimatePresence, motion, useMotionValueEvent, useScroll } from "motion/react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { RollingNumber } from "@/components/motion/Kinetic";
import { Avatar } from "@/components/ui/Misc";
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
  const [hidden, setHidden] = useState(false);
  const [unread, setUnread] = useState(0);
  const { scrollY } = useScroll();

  // L'en-tête se retire au défilement vers le bas et revient dès qu'on remonte.
  useMotionValueEvent(scrollY, "change", (latest) => {
    const previous = scrollY.getPrevious() ?? 0;
    setHidden(latest > 160 && latest > previous && !open);
  });

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
    setOpen(false);
    await logout();
    router.push("/");
  }

  return (
    <motion.header
      className="fixed inset-x-0 top-3 z-40 px-3"
      animate={{ y: hidden ? -110 : 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 32 }}
    >
      <div className="glass mx-auto flex max-w-6xl items-center justify-between gap-3 rounded-2xl border border-line px-3 py-2 shadow-[0_10px_40px_-12px_rgb(0_0_0/0.6)] sm:px-4">
        <Link href="/" className="group flex items-center gap-2 font-display text-lg font-bold tracking-tight">
          <span className="relative grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 text-sm text-night shadow-[0_0_20px_-4px_rgb(16_185_129/0.8)] transition-transform group-hover:rotate-6">
            A
          </span>
          <span>
            AfriDev<span className="text-ocre-400">.</span>
          </span>
        </Link>

        <nav className="hidden items-center md:flex" aria-label="Navigation principale">
          {links.map((link) => {
            const active = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`relative rounded-xl px-3.5 py-2 text-sm transition-colors ${active ? "text-ink" : "text-muted hover:text-ink"}`}
              >
                {active && (
                  <motion.span layoutId="nav-active" className="absolute inset-0 -z-10 rounded-xl border border-line bg-panel-2" transition={{ type: "spring", stiffness: 380, damping: 32 }} />
                )}
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-1.5">
          {status === "authenticated" && user ? (
            <>
              <Link href="/publier" className="btn-primary hidden px-3.5 py-2 text-sm sm:inline-flex">
                + Publier
              </Link>
              <Link href="/notifications" className="relative grid h-10 w-10 place-items-center rounded-xl text-muted transition-colors hover:bg-white/5 hover:text-ink" aria-label={`Notifications (${unread} non lues)`}>
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
                  <path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                  <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
                </svg>
                <AnimatePresence>
                  {unread > 0 && (
                    <motion.span
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                      className="absolute -right-0.5 -top-0.5 grid min-w-5 place-items-center rounded-full bg-ocre-500 px-1 text-[11px] font-bold text-night"
                    >
                      <RollingNumber value={Math.min(unread, 99)} />
                    </motion.span>
                  )}
                </AnimatePresence>
              </Link>
              <Link href={`/membres/${user.username}`} className="hidden rounded-xl p-1 transition-colors hover:bg-white/5 sm:block" title="Mon profil public">
                <Avatar author={{ display_name: user.first_name || user.username, avatar: null }} size={32} />
              </Link>
            </>
          ) : status === "anonymous" ? (
            <>
              <Link href="/connexion" className="rounded-xl px-3 py-2 text-sm font-medium text-muted hover:text-ink">
                Connexion
              </Link>
              <Link href="/inscription" className="btn-primary hidden px-3.5 py-2 text-sm sm:inline-flex">
                Rejoindre
              </Link>
            </>
          ) : null}
          <button
            type="button"
            className="grid h-10 w-10 place-items-center rounded-xl hover:bg-white/5 md:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? "Fermer le menu" : "Ouvrir le menu"}
            onClick={() => setOpen((value) => !value)}
          >
            <span className="relative block h-3 w-5" aria-hidden>
              <motion.span className="absolute left-0 top-0 h-0.5 w-5 rounded bg-ink" animate={open ? { rotate: 45, y: 5 } : { rotate: 0, y: 0 }} />
              <motion.span className="absolute bottom-0 left-0 h-0.5 w-5 rounded bg-ink" animate={open ? { rotate: -45, y: -5 } : { rotate: 0, y: 0 }} />
            </span>
          </button>
        </div>
      </div>

      <AnimatePresence>
        {open && (
          <motion.nav
            id="mobile-nav"
            aria-label="Navigation mobile"
            initial={{ opacity: 0, y: -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.98 }}
            className="glass mx-auto mt-2 max-w-6xl rounded-2xl border border-line p-2 md:hidden"
            onClick={() => setOpen(false)}
          >
            {links.map((link, index) => (
              <motion.div key={link.href} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.04 * index }}>
                <Link href={link.href} className="block rounded-xl px-3 py-3 text-sm hover:bg-white/5">
                  {link.label}
                </Link>
              </motion.div>
            ))}
            <div className="my-2 h-px bg-line" />
            {status === "authenticated" && user ? (
              <>
                <Link href="/publier" className="block rounded-xl px-3 py-3 text-sm font-semibold text-brand-300">+ Publier</Link>
                <Link href="/notifications" className="block rounded-xl px-3 py-3 text-sm">Notifications {unread > 0 ? `(${unread})` : ""}</Link>
                <Link href={`/membres/${user.username}`} className="block rounded-xl px-3 py-3 text-sm">Mon profil public</Link>
                <Link href="/parametres" className="block rounded-xl px-3 py-3 text-sm">Paramètres du profil</Link>
                <button type="button" onClick={handleLogout} className="block w-full rounded-xl px-3 py-3 text-left text-sm text-rose-300">
                  Se déconnecter
                </button>
              </>
            ) : (
              <Link href="/inscription" className="block rounded-xl px-3 py-3 text-sm font-semibold text-brand-300">Créer un compte</Link>
            )}
          </motion.nav>
        )}
      </AnimatePresence>

      {status === "authenticated" && (
        <div className="mx-auto mt-1 hidden max-w-6xl justify-end gap-4 px-4 text-xs text-muted md:flex">
          <Link href="/parametres" className="hover:text-ink">Paramètres du profil</Link>
          <button type="button" onClick={handleLogout} className="hover:text-ink">Se déconnecter</button>
        </div>
      )}
    </motion.header>
  );
}
