"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Loading } from "@/components/ui/Feedback";
import { useAuth } from "@/lib/auth/AuthProvider";

/** Redirige vers la connexion si la session est absente. La vraie protection reste côté API. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "anonymous") {
      router.replace(`/connexion?next=${encodeURIComponent(pathname)}`);
    }
  }, [status, router, pathname]);

  if (status !== "authenticated") return <Loading label="Vérification de la session…" />;
  return <>{children}</>;
}
