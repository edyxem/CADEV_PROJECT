import type { Metadata } from "next";

import { FeedView } from "@/components/community/FeedView";

export const metadata: Metadata = { title: "Questions" };

export default function QuestionsPage() {
  return <FeedView questionsOnly />;
}
