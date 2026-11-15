"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { EmailConfirmation } from "@/components/layout/EmailConfirmation";

function VerifyEmail() {
  const params = useSearchParams();
  return (
    <EmailConfirmation
      endpoint="/auth/email/verify/"
      body={{ uid: params.get("uid") ?? "", token: params.get("token") ?? "" }}
      title="Vérification de l'adresse"
    />
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmail />
    </Suspense>
  );
}
