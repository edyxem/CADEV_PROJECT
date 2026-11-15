/**
 * Client HTTP de l'API AfriDev.
 *
 * - L'access token est gardé en mémoire uniquement (jamais dans localStorage).
 * - Le refresh token vit dans un cookie HttpOnly posé par l'API : on l'envoie avec
 *   `credentials: "include"` sur les routes /auth/.
 * - Sur une réponse 401, une seule tentative de renouvellement est faite, puis la
 *   requête est rejouée.
 */

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"
).replace(/\/$/, "");

export type FieldErrors = Record<string, string[]>;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly errors: FieldErrors;

  constructor(status: number, detail: string, code: string, errors: FieldErrors = {}) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.errors = errors;
  }

  /** Premier message d'erreur d'un champ, s'il existe. */
  field(name: string): string | undefined {
    const messages = this.errors[name];
    return Array.isArray(messages) ? String(messages[0]) : undefined;
  }
}

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
const listeners = new Set<(token: string | null) => void>();

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
  listeners.forEach((listener) => listener(token));
}

/** Prévient l'application quand la session change (connexion, expiration). */
export function onAccessTokenChange(listener: (token: string | null) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = await response.json();
    return new ApiError(
      response.status,
      body.detail ?? "Une erreur est survenue.",
      body.code ?? "error",
      body.errors ?? {},
    );
  } catch {
    return new ApiError(response.status, "Le serveur est momentanément indisponible.", "server_error");
  }
}

/** Renouvelle l'access token grâce au cookie ; les appels simultanés partagent la même requête. */
export function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: "POST",
      credentials: "include",
    })
      .then(async (response) => {
        if (!response.ok) {
          setAccessToken(null);
          return false;
        }
        const body = (await response.json()) as { access: string };
        setAccessToken(body.access);
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
  /** Envoie le cookie de session (routes /auth/). */
  withCredentials?: boolean;
  signal?: AbortSignal;
}

export function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(`${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`);
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });
  return url.toString();
}

export async function api<T>(path: string, options: RequestOptions = {}, retry = true): Promise<T> {
  const { method = "GET", body, query, withCredentials = false, signal } = options;
  const headers: Record<string, string> = { Accept: "application/json" };
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  if (body !== undefined && !isForm) {
    headers["Content-Type"] = "application/json";
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
      credentials: withCredentials ? "include" : "same-origin",
      signal,
    });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new ApiError(0, "Connexion impossible : vérifiez votre réseau.", "network_error");
  }

  if (response.status === 401 && retry && accessToken !== null) {
    const renewed = await refreshSession();
    if (renewed) {
      return api<T>(path, options, false);
    }
  }
  if (!response.ok) {
    throw await parseError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
