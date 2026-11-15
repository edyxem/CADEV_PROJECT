"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { EmailConfirmation } from "@/components/layout/EmailConfirmation";

function ConfirmEmail() {
  const params = useSearchParams();
  return <EmailConfirmation endpoint="/auth/email/change/confirm/" body={{ token: params.get("token") ?? "" }} title="Nouvelle adresse e-mail" />;
}

export default function ConfirmEmailPage() {
  return (
    <Suspense>
      <ConfirmEmail />
    </Suspense>
  );
}
