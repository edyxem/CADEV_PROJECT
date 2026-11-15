"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AuthShell } from "@/components/layout/AuthShell";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Feedback";
import { Input } from "@/components/ui/Field";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await register(form);
      router.push("/parametres?bienvenue=1");
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setSubmitting(false);
    }
  }

  const update = (field: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((previous) => ({ ...previous, [field]: event.target.value }));

  return (
    <AuthShell title="Créer un compte" subtitle="Trois informations suffisent ; vous compléterez votre profil ensuite.">
      {error && error.code !== "validation_error" && <Alert kind="error">{error.message}</Alert>}
      <form onSubmit={onSubmit} noValidate>
        <Input label="Nom d'utilisateur" value={form.username} onChange={update("username")} hint="3 à 30 caractères : lettres, chiffres et tiret bas." error={error?.field("username")} autoComplete="username" required />
        <Input label="Adresse e-mail" type="email" value={form.email} onChange={update("email")} error={error?.field("email")} autoComplete="email" required />
        <Input label="Mot de passe" type="password" value={form.password} onChange={update("password")} hint="10 caractères minimum, évitez les mots de passe courants." error={error?.field("password")} autoComplete="new-password" required />
        <Button type="submit" loading={submitting} className="w-full">Créer mon compte</Button>
      </form>
      <p className="mt-4 text-center text-sm text-muted">
        Déjà membre ? <Link href="/connexion" className="text-brand-300 underline">Se connecter</Link>
      </p>
    </AuthShell>
  );
}
