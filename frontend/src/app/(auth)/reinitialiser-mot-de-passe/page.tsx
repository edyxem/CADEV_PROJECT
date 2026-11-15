"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { AuthShell } from "@/components/layout/AuthShell";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Feedback";
import { Input } from "@/components/ui/Field";
import { api, ApiError } from "@/lib/api/client";

function ResetForm() {
  const params = useSearchParams();
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const mismatch = confirmation.length > 0 && confirmation !== password;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (mismatch) return;
    setSubmitting(true);
    setError(null);
    try {
      await api("/auth/password/reset/confirm/", { method: "POST", body: { uid, token, new_password: password } });
      setDone(true);
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setSubmitting(false);
    }
  }

  if (!uid || !token) {
    return (
      <AuthShell title="Lien incomplet" subtitle="Ce lien de réinitialisation est invalide.">
        <Alert kind="error">Ouvrez le lien reçu par e-mail en entier, ou demandez-en un nouveau.</Alert>
        <ButtonLink href="/mot-de-passe-oublie" className="w-full">
          Demander un nouveau lien
        </ButtonLink>
      </AuthShell>
    );
  }

  const linkError = error?.field("token") ?? error?.field("uid");

  return (
    <AuthShell title="Nouveau mot de passe" subtitle="Choisissez un mot de passe solide, différent de l'ancien.">
      {done ? (
        <>
          <Alert kind="success">Votre mot de passe a été modifié. Vous pouvez vous connecter.</Alert>
          <ButtonLink href="/connexion" className="w-full">
            Se connecter
          </ButtonLink>
        </>
      ) : (
        <form onSubmit={onSubmit} noValidate>
          {error && error.code !== "validation_error" && <Alert kind="error">{error.message}</Alert>}
          {linkError && <Alert kind="error">{linkError}</Alert>}
          <Input label="Nouveau mot de passe" type="password" value={password} onChange={(e) => setPassword(e.target.value)} error={error?.field("new_password")} autoComplete="new-password" required />
          <Input
            label="Confirmation"
            type="password"
            value={confirmation}
            onChange={(e) => setConfirmation(e.target.value)}
            error={mismatch ? "Les deux mots de passe ne correspondent pas." : undefined}
            autoComplete="new-password"
            required
          />
          <Button type="submit" loading={submitting} disabled={!password || mismatch} className="w-full">
            Enregistrer
          </Button>
          <p className="mt-4 text-center text-sm text-muted">
            <Link href="/mot-de-passe-oublie" className="text-brand-300 underline">
              Demander un nouveau lien
            </Link>
          </p>
        </form>
      )}
    </AuthShell>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetForm />
    </Suspense>
  );
}
