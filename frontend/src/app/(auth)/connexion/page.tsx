"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Feedback";
import { Input } from "@/components/ui/Field";
import { Card } from "@/components/ui/Misc";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";

function safeNext(value: string | null): string {
  // Évite les redirections ouvertes : uniquement des chemins internes.
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/fil";
}

function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(identifier, password);
      router.push(next);
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="mx-auto max-w-md">
      <h1 className="mb-1 text-2xl font-semibold">Connexion</h1>
      <p className="mb-6 text-sm text-muted">Avec votre adresse e-mail ou votre nom d'utilisateur.</p>
      {error && <Alert kind="error">{error.message}</Alert>}
      <form onSubmit={onSubmit} noValidate>
        <Input label="E-mail ou nom d'utilisateur" value={identifier} onChange={(e) => setIdentifier(e.target.value)} autoComplete="username" required />
        <Input label="Mot de passe" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        <Button type="submit" loading={submitting} className="w-full">Se connecter</Button>
      </form>
      <p className="mt-4 text-center text-sm text-muted">
        Pas encore de compte ? <Link href="/inscription" className="text-brand-700 underline">Créer un compte</Link>
      </p>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
