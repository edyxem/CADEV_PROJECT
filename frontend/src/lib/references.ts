"use client";

import type { Paginated, Ref } from "@/lib/api/types";
import { useApi } from "@/lib/useApi";

/** Référentiels publics pour alimenter les filtres et formulaires. */
export function useReferences() {
  const categories = useApi<Paginated<Ref>>("/categories/", { page_size: 100 });
  const technologies = useApi<Paginated<Ref>>("/technologies/", { page_size: 100 });
  const countries = useApi<Paginated<{ code: string; name: string }>>("/countries/", { page_size: 100 });
  return {
    categories: categories.data?.results ?? [],
    technologies: technologies.data?.results ?? [],
    countries: countries.data?.results ?? [],
  };
}

export function toOptions(items: Ref[], emptyLabel: string) {
  return [{ value: "", label: emptyLabel }, ...items.map((item) => ({ value: item.slug, label: item.name }))];
}
