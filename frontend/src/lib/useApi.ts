"use client";

import { useCallback, useEffect, useState } from "react";

import { api, ApiError, type RequestOptions } from "@/lib/api/client";

interface Result<T> {
  key: string | null;
  data: T | null;
  error: ApiError | null;
}

/**
 * Charge une ressource de l'API et expose les états de chargement, d'erreur et de données.
 * `path = null` désactive la requête (ex. utilisateur non connecté).
 *
 * L'état « chargement » est dérivé de la clé de requête : pas de setState synchrone dans l'effet.
 * Les données précédentes restent affichées pendant le chargement de la page suivante.
 */
export function useApi<T>(path: string | null, query?: RequestOptions["query"]) {
  const [version, setVersion] = useState(0);
  const queryKey = JSON.stringify(query ?? {});
  const key = path === null ? null : `${path}?${queryKey}#${version}`;
  const [result, setResult] = useState<Result<T>>({ key: null, data: null, error: null });

  useEffect(() => {
    if (path === null || key === null) return;
    const controller = new AbortController();
    api<T>(path, { query: JSON.parse(queryKey), signal: controller.signal })
      .then((data) => setResult({ key, data, error: null }))
      .catch((error: unknown) => {
        if ((error as Error).name === "AbortError") return;
        const apiError =
          error instanceof ApiError ? error : new ApiError(0, "Erreur inattendue.", "unknown");
        setResult({ key, data: null, error: apiError });
      });
    return () => controller.abort();
  }, [path, queryKey, key]);

  const reload = useCallback(() => setVersion((value) => value + 1), []);
  if (key === null) {
    return { data: null, error: null, loading: false, reload };
  }
  const settled = result.key === key;
  return {
    data: result.data,
    error: settled ? result.error : null,
    loading: !settled,
    reload,
  };
}
