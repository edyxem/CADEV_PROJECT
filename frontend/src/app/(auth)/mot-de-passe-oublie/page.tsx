"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { AuthShell } from "@/components/layout/AuthShell";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Feedback";
import { Input } from "@/components/ui/Field";
import { api, ApiError } from "@/lib/api/client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api("/auth/password/reset/", { method: "POST", body: { email } });
      setSent(true);
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell title="Mot de passe oublié" subtitle="Recevez un lien pour choisir un nouveau mot de passe.">
      {sent ? (
        <Alert kind="success">
          Si un compte correspond à cette adresse, un e-mail contenant un lien de réinitialisation vient d&apos;être
          envoyé. Le lien est valable pour une durée limitée.
        </Alert>
      ) : (
        <form onSubmit={onSubmit} noValidate>
          {error && error.code !== "validation_error" && <Alert kind="error">{error.message}</Alert>}
          <Input label="Adresse e-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} error={error?.field("email")} autoComplete="email" required />
          <Button type="submit" loading={submitting} disabled={!email.trim()} className="w-full">
            Envoyer le lien
          </Button>
        </form>
      )}
      <p className="mt-4 text-center text-sm text-muted">
        <Link href="/connexion" className="text-brand-300 underline">
          Retour à la connexion
        </Link>
      </p>
    </AuthShell>
  );
}
