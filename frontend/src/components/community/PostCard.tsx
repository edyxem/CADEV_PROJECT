import Link from "next/link";

import { AuthorLine, Badge, Card } from "@/components/ui/Misc";
import type { Post } from "@/lib/api/types";
import { formatDate, label, POST_TYPES } from "@/lib/labels";

export function PostCard({ post }: { post: Post }) {
  const isQuestion = post.type === "QUESTION";
  return (
    <Card>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Badge tone={isQuestion ? "accent" : "brand"}>{label(POST_TYPES, post.type)}</Badge>
        {post.category && <Badge>{post.category.name}</Badge>}
        {isQuestion && post.has_accepted_answer && <Badge tone="brand">✓ Résolue</Badge>}
      </div>
      <h3 className="text-lg font-semibold leading-snug">
        <Link href={`/publications/${post.id}`} className="hover:text-brand-700 hover:underline">
          {post.title}
        </Link>
      </h3>
      {post.excerpt && <p className="mt-1 line-clamp-2 text-sm text-muted">{post.excerpt}</p>}
      {post.technologies.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {post.technologies.map((technology) => (
            <span key={technology.id} className="rounded bg-stone-100 px-1.5 py-0.5 text-xs text-stone-700">
              {technology.name}
            </span>
          ))}
        </div>
      )}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <AuthorLine author={post.author}>
          <span>· {formatDate(post.published_at)}</span>
        </AuthorLine>
        <div className="flex gap-3 text-xs text-muted">
          <span>▲ {post.vote_count}</span>
          <span>{isQuestion ? `${post.answer_count} réponse(s)` : `${post.comment_count} commentaire(s)`}</span>
        </div>
      </div>
    </Card>
  );
}
