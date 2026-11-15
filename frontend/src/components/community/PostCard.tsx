"use client";

import { motion } from "motion/react";
import Link from "next/link";

import { AuthorLine, Badge } from "@/components/ui/Misc";
import type { Post } from "@/lib/api/types";
import { formatDate, label, POST_TYPES } from "@/lib/labels";

export function PostCard({ post }: { post: Post }) {
  const isQuestion = post.type === "QUESTION";
  return (
    <motion.article
      whileHover={{ y: -3 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
      className="group relative rounded-2xl border border-line bg-panel p-5 transition-colors hover:border-brand-400/35"
    >
      <span
        aria-hidden
        className={`absolute inset-y-5 left-0 w-[3px] rounded-r-full ${isQuestion ? "bg-ocre-400" : "bg-brand-400"} opacity-60 transition-opacity group-hover:opacity-100`}
      />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge tone={isQuestion ? "accent" : "brand"}>{label(POST_TYPES, post.type)}</Badge>
        {post.category && <Badge>{post.category.name}</Badge>}
        {isQuestion && post.has_accepted_answer && <Badge tone="brand">✓ Résolue</Badge>}
      </div>
      <h3 className="font-display text-lg font-semibold leading-snug">
        <Link href={`/publications/${post.id}`} className="after:absolute after:inset-0 group-hover:text-brand-200">
          {post.title}
        </Link>
      </h3>
      {post.excerpt && <p className="mt-1.5 line-clamp-2 text-sm text-muted">{post.excerpt}</p>}
      {post.technologies.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {post.technologies.map((technology) => (
            <span key={technology.id} className="rounded-md bg-white/[0.04] px-2 py-0.5 font-mono text-[11px] text-muted">
              {technology.name}
            </span>
          ))}
        </div>
      )}
      <div className="relative z-10 mt-4 flex flex-wrap items-center justify-between gap-2">
        <AuthorLine author={post.author}>
          <span>· {formatDate(post.published_at)}</span>
        </AuthorLine>
        <div className="flex gap-4 text-xs text-muted">
          <span className={post.has_voted ? "text-brand-300" : ""}>▲ {post.vote_count}</span>
          <span>{isQuestion ? `${post.answer_count} réponse(s)` : `${post.comment_count} commentaire(s)`}</span>
        </div>
      </div>
    </motion.article>
  );
}
