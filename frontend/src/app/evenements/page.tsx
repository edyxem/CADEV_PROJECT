"use client";

import { motion } from "motion/react";
import { useState } from "react";

import { EventCard } from "@/components/events/EventCard";
import { Stagger, StaggerItem } from "@/components/motion/Reveal";
import { EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { PageTitle, Pagination } from "@/components/ui/Misc";
import type { EventItem, Paginated } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useApi } from "@/lib/useApi";

const TABS = [
  { value: "upcoming", label: "À venir" },
  { value: "past", label: "Passés" },
  { value: "mine", label: "Mes inscriptions" },
];

export default function EventsPage() {
  const { status } = useAuth();
  const [tab, setTab] = useState("upcoming");
  const [page, setPage] = useState(1);
  const mine = tab === "mine";
  const result = useApi<Paginated<EventItem>>(mine ? "/events/mine/" : "/events/", mine ? { page } : { when: tab, page });
  const tabs = status === "authenticated" ? TABS : TABS.filter((item) => item.value !== "mine");

  return (
    <div>
      <PageTitle eyebrow="Agenda" title="Événements" subtitle="Meetups, ateliers, webinaires et hackathons organisés par la communauté, en ligne ou près de chez vous." />
      <div className="mb-6 inline-flex rounded-2xl border border-line bg-panel p-1" role="tablist" aria-label="Période">
        {tabs.map((item) => (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={tab === item.value}
            onClick={() => {
              setTab(item.value);
              setPage(1);
            }}
            className={`relative rounded-xl px-4 py-2 text-sm transition-colors ${tab === item.value ? "text-ink" : "text-muted hover:text-ink"}`}
          >
            {tab === item.value && <motion.span layoutId="event-tab" className="absolute inset-0 -z-10 rounded-xl bg-panel-2" transition={{ type: "spring", stiffness: 380, damping: 32 }} />}
            {item.label}
          </button>
        ))}
      </div>
      {result.loading && !result.data && <Loading />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {result.data?.count === 0 && <EmptyState title="Aucun événement ici">{mine ? "Inscrivez-vous à un événement à venir pour le retrouver ici." : "Revenez bientôt : de nouveaux événements sont publiés régulièrement."}</EmptyState>}
      <Stagger key={JSON.stringify([tab, page, result.data?.count])} className={`grid gap-3 transition-opacity lg:grid-cols-2 ${result.loading ? "opacity-60" : ""}`}>
        {result.data?.results.map((event) => (
          <StaggerItem key={event.id}>
            <EventCard event={event} />
          </StaggerItem>
        ))}
      </Stagger>
      {result.data && <Pagination page={page} count={result.data.count} onChange={setPage} />}
    </div>
  );
}
