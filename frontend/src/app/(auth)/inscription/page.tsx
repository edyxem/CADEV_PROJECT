"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AuthShell } from "@/components/layout/AuthShell";
import { AvatarChooser } from "@/components/profiles/AvatarPicker";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Feedback";
import { Input } from "@/components/ui/Field";
import { api, ApiError } from "@/lib/api/client";
import type { OwnProfile } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";

export default function RegisterPage() {
  const { register, setAvatar } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [photo, setPhoto] = useState<File | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await register(form);
    } catch (caught) {
      setError(caught as ApiError);
      setSubmitting(false);
      return;
    }
    // Le compte existe : la photo est envoyée ensuite. Un échec n'empêche pas l'inscription,
    // la photo pourra être ajoutée depuis les paramètres.
    let photoFailed = false;
    if (photo) {
      try {
        const body = new FormData();
        body.append("avatar", photo);
        const profile = await api<OwnProfile>("/profiles/me/avatar/", { method: "PUT", body });
        setAvatar(profile.avatar);
      } catch {
        photoFailed = true;
      }
    }
    router.push(photoFailed ? "/parametres?bienvenue=1&photo=echec" : "/parametres?bienvenue=1");
  }

  const update = (field: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((previous) => ({ ...previous, [field]: event.target.value }));

  return (
    <AuthShell title="Créer un compte" subtitle="Trois informations suffisent ; vous compléterez votre profil ensuite.">
      {error && error.code !== "validation_error" && <Alert kind="error">{error.message}</Alert>}
      <form onSubmit={onSubmit} noValidate>
        <AvatarChooser name={form.username} file={photo} onChange={setPhoto} />
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
