"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useState } from "react";

import { JoinButton } from "@/components/communities/JoinButton";
import { PostCard } from "@/components/community/PostCard";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/Reveal";
import { EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { Badge, Card, Pagination } from "@/components/ui/Misc";
import type { CommunityItem, Paginated, Post } from "@/lib/api/types";
import { COMMUNITY_KINDS, label } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

export default function CommunityPage() {
  const { slug } = useParams<{ slug: string }>();
  const community = useApi<CommunityItem>(`/communities/${slug}/`);
  const [page, setPage] = useState(1);
  const posts = useApi<Paginated<Post>>(`/communities/${slug}/posts/`, { page });
  const [override, setOverride] = useState<CommunityItem | null>(null);

  if (community.loading && !community.data) return <Loading />;
  if (community.error) return <ErrorState error={community.error} onRetry={community.reload} />;
  const data = override ?? community.data;
  if (!data) return null;

  return (
    <div>
      <Reveal>
        <Link href="/communautes" className="text-sm text-muted hover:text-ink">
          ← Toutes les communautés
        </Link>
        <div className="grain relative mt-4 overflow-hidden rounded-[2rem] border border-line bg-gradient-to-br from-brand-500/15 via-panel to-ocre-500/10 p-6 sm:p-10">
          <Badge tone="accent">{label(COMMUNITY_KINDS, data.kind)}</Badge>
          <h1 className="mt-3 font-display text-3xl font-bold sm:text-5xl">{data.name}</h1>
          {data.description && <p className="mt-3 max-w-2xl text-muted">{data.description}</p>}
          <div className="mt-6 flex flex-wrap items-center gap-4">
            <JoinButton community={data} onChange={setOverride} />
            <p className="text-sm text-muted">{data.member_count} membre(s)</p>
            {data.my_role && (
              <Link href={`/publier?community=${data.slug}`} className="text-sm text-brand-300 underline">
                Publier dans cette communauté
              </Link>
            )}
          </div>
        </div>
      </Reveal>

      {data.rules && (
        <Card className="mt-6">
          <h2 className="mb-2 font-display text-lg font-semibold">Règles de la communauté</h2>
          <p className="whitespace-pre-line text-sm text-muted">{data.rules}</p>
        </Card>
      )}

      <h2 className="mb-3 mt-10 font-display text-xl font-semibold">Publications</h2>
      {posts.loading && !posts.data && <Loading />}
      {posts.error && <ErrorState error={posts.error} onRetry={posts.reload} />}
      {posts.data?.count === 0 && <EmptyState title="Aucune publication pour l'instant">Rejoignez la communauté et lancez la première discussion.</EmptyState>}
      <Stagger key={JSON.stringify([page, posts.data?.count])} className="space-y-3">
        {posts.data?.results.map((post) => (
          <StaggerItem key={post.id}>
            <PostCard post={post} />
          </StaggerItem>
        ))}
      </Stagger>
      {posts.data && <Pagination page={page} count={posts.data.count} onChange={setPage} />}
    </div>
  );
}
