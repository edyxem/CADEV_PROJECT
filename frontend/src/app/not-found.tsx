import { ButtonLink } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/Feedback";

export default function NotFound() {
  return (
    <EmptyState title="Page introuvable">
      <p className="mb-4">Cette page n'existe pas ou a été déplacée.</p>
      <ButtonLink href="/fil">Retour au fil</ButtonLink>
    </EmptyState>
  );
}
