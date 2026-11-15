"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { ConversationList } from "@/components/messaging/ConversationList";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Feedback";
import { Input, Textarea } from "@/components/ui/Field";
import { Card, PageTitle } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { Conversation } from "@/lib/api/types";

function NewConversation() {
  const router = useRouter();
  const [username, setUsername] = useState(useSearchParams().get("to") ?? "");
  const [content, setContent] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const conversation = await api<Conversation>("/conversations/", { method: "POST", body: { username: username.trim(), content } });
      router.push(`/messages/${conversation.id}`);
    } catch (caught) {
      setError(caught as ApiError);
      setSubmitting(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[20rem_1fr]">
      <ConversationList />
      <Card>
        <h2 className="mb-4 font-display text-xl font-semibold">Nouvelle conversation</h2>
        {error && error.code !== "validation_error" && <Alert kind="error">{error.message}</Alert>}
        <form onSubmit={submit} noValidate>
          <Input label="Destinataire (nom d'utilisateur)" value={username} onChange={(e) => setUsername(e.target.value)} error={error?.field("username")} placeholder="ex. kofi_mensah" required />
          <Textarea label="Message" value={content} onChange={(e) => setContent(e.target.value)} error={error?.field("content")} rows={5} required />
          <Button type="submit" loading={submitting} disabled={!username.trim() || !content.trim()}>
            Envoyer
          </Button>
        </form>
        <p className="mt-4 text-xs text-muted">Les messages sont privés. Vous pouvez bloquer ou signaler un membre depuis la conversation.</p>
      </Card>
    </div>
  );
}

export default function MessagesPage() {
  return (
    <RequireAuth>
      <PageTitle eyebrow="Messagerie" title="Messages" subtitle="Échangez en privé avec les autres membres." />
      <Suspense>
        <NewConversation />
      </Suspense>
    </RequireAuth>
  );
}
