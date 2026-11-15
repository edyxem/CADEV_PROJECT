"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState, Loading } from "@/components/ui/Feedback";
import { Card, PageTitle, Pagination } from "@/components/ui/Misc";
import { api } from "@/lib/api/client";
import type { AppNotification, Paginated } from "@/lib/api/types";
import { formatDate } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

// Liens frontend existants dans cette version ; les autres modules arrivent plus tard.
const SUPPORTED_PREFIXES = ["/publications/", "/projets/", "/membres/"];

function NotificationsContent() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const list = useApi<Paginated<AppNotification>>("/notifications/", { page, is_read: unreadOnly ? "false" : undefined });

  async function open(notification: AppNotification) {
    if (!notification.is_read) {
      await api(`/notifications/${notification.id}/read/`, { method: "POST" }).catch(() => undefined);
    }
    if (SUPPORTED_PREFIXES.some((prefix) => notification.target_url.startsWith(prefix))) {
      router.push(notification.target_url);
    } else {
      list.reload();
    }
  }

  async function readAll() {
    await api("/notifications/read-all/", { method: "POST" });
    list.reload();
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageTitle title="Notifications" action={<Button type="button" variant="secondary" onClick={readAll}>Tout marquer comme lu</Button>} />
      <label className="mb-4 flex items-center gap-2 text-sm">
        <input type="checkbox" checked={unreadOnly} onChange={(e) => { setUnreadOnly(e.target.checked); setPage(1); }} /> Non lues uniquement
      </label>
      {list.loading && !list.data && <Loading />}
      {list.error && <ErrorState error={list.error} onRetry={list.reload} />}
      {list.data?.count === 0 && <EmptyState title="Rien de nouveau">Les réponses, demandes et tâches qui vous concernent apparaîtront ici.</EmptyState>}
      <div className="space-y-2">
        {list.data?.results.map((notification) => (
          <Card key={notification.id} className={notification.is_read ? "opacity-70" : "border-brand-600"}>
            <button type="button" onClick={() => open(notification)} className="w-full text-left">
              <p className="font-medium">{!notification.is_read && <span className="mr-2 inline-block h-2 w-2 rounded-full bg-accent-500" aria-label="Non lue" />}{notification.title}</p>
              {notification.message && <p className="mt-1 text-sm text-muted">{notification.message}</p>}
              <p className="mt-1 text-xs text-muted">{formatDate(notification.created_at)}</p>
            </button>
          </Card>
        ))}
      </div>
      {list.data && <Pagination page={page} count={list.data.count} onChange={setPage} />}
    </div>
  );
}

export default function NotificationsPage() {
  return (
    <RequireAuth>
      <NotificationsContent />
    </RequireAuth>
  );
}
