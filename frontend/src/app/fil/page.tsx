import type { Metadata } from "next";

import { FeedView } from "@/components/community/FeedView";

export const metadata: Metadata = { title: "Fil communautaire" };

export default function FeedPage() {
  return <FeedView />;
}
