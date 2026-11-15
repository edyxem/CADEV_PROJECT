"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { BookmarkButton, ReportButton, VoteButton } from "@/components/community/Actions";
import { Answers, Comments } from "@/components/community/Discussion";
import { Button } from "@/components/ui/Button";
import { Alert, ErrorState, Loading } from "@/components/ui/Feedback";
import { AuthorLine, Badge, Card, RichText } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { PostDetail } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDate, label, POST_TYPES } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

export default function PostPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { status } = useAuth();
  const post = useApi<PostDetail>(`/posts/${id}/`);
  const [bookmarked, setBookmarked] = useState<boolean | null>(null);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  if (post.loading && !post.data) return <Loading />;
  if (post.error) return <ErrorState error={post.error} onRetry={post.reload} />;
  if (!post.data) return null;
  const data = post.data;
  const isBookmarked = bookmarked ?? data.has_bookmarked;

  async function toggleBookmark() {
    try {
      const result = await api<{ bookmarked: boolean }>(`/posts/${data.id}/bookmark/`, { method: "POST", body: { active: !isBookmarked } });
      setBookmarked(result.bookmarked);
    } catch (caught) {
      setMessage({ kind: "error", text: (caught as ApiError).message });
    }
  }

  async function publishDraft() {
    try {
      await api(`/posts/${data.id}/`, { method: "PATCH", body: { status: "PUBLISHED" } });
      post.reload();
    } catch (caught) {
      const error = caught as ApiError;
      setMessage({ kind: "error", text: error.field("content") ?? error.message });
    }
  }

  async function remove() {
    if (!window.confirm("Supprimer cette publication ? Elle ne sera plus visible.")) return;
    try {
      await api(`/posts/${data.id}/`, { method: "DELETE" });
      router.push("/fil");
    } catch (caught) {
      setMessage({ kind: "error", text: (caught as ApiError).message });
    }
  }

  return (
    <article className="mx-auto max-w-3xl">
      {message && <Alert kind={message.kind}>{message.text}</Alert>}
      {data.status === "DRAFT" && (
        <Alert>
          Ce brouillon n'est visible que par vous.{" "}
          <button type="button" onClick={publishDraft} className="font-medium underline">Publier maintenant</button>
        </Alert>
      )}
      {data.status === "HIDDEN" && <Alert kind="error">Cette publication a été masquée par la modération.</Alert>}
      <Card>
        <div className="mb-3 flex flex-wrap gap-2">
          <Badge tone={data.type === "QUESTION" ? "accent" : "brand"}>{label(POST_TYPES, data.type)}</Badge>
          {data.category && <Badge>{data.category.name}</Badge>}
          {data.technologies.map((technology) => <Badge key={technology.id}>{technology.name}</Badge>)}
        </div>
        <h1 className="text-2xl font-semibold leading-tight">{data.title}</h1>
        <div className="mt-3">
          <AuthorLine author={data.author}>
            <span>· {formatDate(data.published_at ?? data.created_at)}</span>
          </AuthorLine>
        </div>
        <div className="mt-4"><RichText html={data.content} /></div>
        {data.environment && (
          <div className="mt-4 rounded-lg bg-panel-2 p-3 text-sm">
            <p className="font-medium">Environnement</p>
            <p className="whitespace-pre-line text-muted">{data.environment}</p>
          </div>
        )}
        <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-line pt-4">
          <VoteButton path={`/posts/${data.id}/vote/`} voted={data.has_voted} count={data.vote_count} disabled={data.can_edit} />
          {status === "authenticated" && data.status === "PUBLISHED" && (
            <BookmarkButton active={isBookmarked} onToggle={toggleBookmark} />
          )}
          {data.can_edit && <Button type="button" variant="ghost" onClick={remove} className="text-rose-300">Supprimer</Button>}
          <span className="ml-auto"><ReportButton targetType="POST" targetId={data.id} /></span>
        </div>
      </Card>

      {data.status === "PUBLISHED" && (data.type === "QUESTION" ? <Answers question={data} onAccepted={post.reload} /> : <Comments postId={data.id} />)}
    </article>
  );
}
