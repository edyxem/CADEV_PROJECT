"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Feedback";
import { Input } from "@/components/ui/Field";
import { Card } from "@/components/ui/Misc";
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
    <Card className="mx-auto max-w-md">
      <h1 className="mb-1 text-2xl font-semibold">Créer un compte</h1>
      <p className="mb-6 text-sm text-muted">Trois informations suffisent ; vous compléterez votre profil ensuite.</p>
      {error && error.code !== "validation_error" && <Alert kind="error">{error.message}</Alert>}
      <form onSubmit={onSubmit} noValidate>
        <Input label="Nom d'utilisateur" value={form.username} onChange={update("username")} hint="3 à 30 caractères : lettres, chiffres et tiret bas." error={error?.field("username")} autoComplete="username" required />
        <Input label="Adresse e-mail" type="email" value={form.email} onChange={update("email")} error={error?.field("email")} autoComplete="email" required />
        <Input label="Mot de passe" type="password" value={form.password} onChange={update("password")} hint="10 caractères minimum, évitez les mots de passe courants." error={error?.field("password")} autoComplete="new-password" required />
        <Button type="submit" loading={submitting} className="w-full">Créer mon compte</Button>
      </form>
      <p className="mt-4 text-center text-sm text-muted">
        Déjà membre ? <Link href="/connexion" className="text-brand-700 underline">Se connecter</Link>
      </p>
    </Card>
  );
}
