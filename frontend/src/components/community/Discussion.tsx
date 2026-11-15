"use client";

import { useState, type FormEvent } from "react";

import { ReportButton, VoteButton } from "@/components/community/Actions";
import { Button } from "@/components/ui/Button";
import { Alert, EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { Textarea } from "@/components/ui/Field";
import { AuthorLine, Badge, Card, RichText } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { Answer, Comment, Paginated, PostDetail } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDate } from "@/lib/labels";
import { textToHtml } from "@/lib/text";
import { useApi } from "@/lib/useApi";

function ReplyForm({ onSubmit, label, placeholder }: { onSubmit: (html: string) => Promise<void>; label: string; placeholder?: string }) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await onSubmit(textToHtml(text));
      setText("");
    } catch (caught) {
      const apiError = caught as ApiError;
      setError(apiError.field("content") ?? apiError.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-3">
      <Textarea label={label} value={text} onChange={(e) => setText(e.target.value)} rows={3} placeholder={placeholder} error={error ?? undefined} />
      <Button type="submit" loading={pending} disabled={!text.trim()}>Envoyer</Button>
    </form>
  );
}

export function Comments({ postId }: { postId: string }) {
  const { status } = useAuth();
  const comments = useApi<Paginated<Comment>>(`/posts/${postId}/comments/`, { page_size: 100 });
  const [replyTo, setReplyTo] = useState<string | null>(null);

  async function add(html: string, parent: string | null) {
    await api(`/posts/${postId}/comments/`, { method: "POST", body: { content: html, parent } });
    setReplyTo(null);
    comments.reload();
  }

  const all = comments.data?.results ?? [];
  const roots = all.filter((comment) => comment.parent === null);

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-lg font-semibold">Commentaires ({all.filter((c) => !c.is_removed).length})</h2>
      {comments.loading && !comments.data && <Loading />}
      {comments.error && <ErrorState error={comments.error} onRetry={comments.reload} />}
      <div className="space-y-3">
        {roots.map((comment) => (
          <Card key={comment.id}>
            <CommentBody comment={comment} />
            <div className="ml-4 mt-3 space-y-3 border-l-2 border-line pl-4">
              {all.filter((reply) => reply.parent === comment.id).map((reply) => <CommentBody key={reply.id} comment={reply} />)}
            </div>
            {status === "authenticated" && !comment.is_removed && (
              replyTo === comment.id ? (
                <ReplyForm label="Votre réponse" onSubmit={(html) => add(html, comment.id)} />
              ) : (
                <button type="button" onClick={() => setReplyTo(comment.id)} className="mt-2 text-xs text-brand-300 hover:underline">Répondre</button>
              )
            )}
          </Card>
        ))}
      </div>
      {status === "authenticated" ? (
        <ReplyForm label="Ajouter un commentaire" onSubmit={(html) => add(html, null)} />
      ) : (
        <p className="mt-3 text-sm text-muted">Connectez-vous pour participer à la discussion.</p>
      )}
    </section>
  );
}

function CommentBody({ comment }: { comment: Comment }) {
  if (comment.is_removed || !comment.author) {
    return <p className="text-sm italic text-muted">Commentaire retiré.</p>;
  }
  return (
    <div>
      <AuthorLine author={comment.author}>
        <span>· {formatDate(comment.created_at)}</span>
      </AuthorLine>
      <div className="mt-1">
        <RichText html={comment.content} />
      </div>
      <ReportButton targetType="COMMENT" targetId={comment.id} />
    </div>
  );
}

export function Answers({ question, onAccepted }: { question: PostDetail; onAccepted: () => void }) {
  const { user, status } = useAuth();
  const answers = useApi<Paginated<Answer>>(`/questions/${question.id}/answers/`, { page_size: 100 });
  const [error, setError] = useState<string | null>(null);
  const isAuthor = user?.username === question.author.username;

  async function add(html: string) {
    await api(`/questions/${question.id}/answers/`, { method: "POST", body: { content: html } });
    answers.reload();
  }

  async function toggleAccept(answer: Answer) {
    setError(null);
    try {
      await api(`/answers/${answer.id}/accept/`, { method: answer.is_accepted ? "DELETE" : "POST" });
      answers.reload();
      onAccepted();
    } catch (caught) {
      setError((caught as ApiError).message);
    }
  }

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-lg font-semibold">Réponses ({answers.data?.count ?? 0})</h2>
      {error && <Alert kind="error">{error}</Alert>}
      {answers.loading && !answers.data && <Loading />}
      {answers.error && <ErrorState error={answers.error} onRetry={answers.reload} />}
      {answers.data?.count === 0 && <EmptyState title="Pas encore de réponse">Partagez votre expérience pour aider l'auteur.</EmptyState>}
      <div className="space-y-3">
        {answers.data?.results.map((answer) => (
          <Card key={answer.id} className={answer.is_accepted ? "border-brand-400/60 ring-1 ring-brand-400/50" : ""}>
            <div className="flex gap-3">
              <VoteButton path={`/answers/${answer.id}/vote/`} voted={answer.has_voted} count={answer.vote_count} disabled={answer.author.username === user?.username} />
              <div className="min-w-0 flex-1">
                {answer.is_accepted && <Badge tone="brand">✓ Réponse acceptée</Badge>}
                <AuthorLine author={answer.author}>
                  <span>· {formatDate(answer.created_at)}</span>
                </AuthorLine>
                <div className="mt-2"><RichText html={answer.content} /></div>
                <div className="mt-2 flex items-center gap-4">
                  {isAuthor && answer.author.username !== user?.username && (
                    <button type="button" onClick={() => toggleAccept(answer)} className="text-xs font-medium text-brand-300 hover:underline">
                      {answer.is_accepted ? "Retirer l'acceptation" : "Accepter cette réponse"}
                    </button>
                  )}
                  <ReportButton targetType="ANSWER" targetId={answer.id} />
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
      {status === "authenticated" && !isAuthor && <ReplyForm label="Votre réponse" onSubmit={add} placeholder="Expliquez votre solution, idéalement avec un exemple." />}
      {status !== "authenticated" && <p className="mt-3 text-sm text-muted">Connectez-vous pour répondre.</p>}
    </section>
  );
}
