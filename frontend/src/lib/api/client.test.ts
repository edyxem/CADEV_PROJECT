import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, buildUrl, getAccessToken, refreshSession, setAccessToken } from "./client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("client API", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken(null);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("construit l'URL en ignorant les paramètres vides", () => {
    const url = buildUrl("/posts/", { type: "QUESTION", q: "", page: 2, category: undefined });

    expect(url).toBe("http://localhost:8000/api/v1/posts/?type=QUESTION&page=2");
  });

  it("envoie l'access token en en-tête Authorization", async () => {
    setAccessToken("jeton");
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { ok: true }));

    await api("/auth/me/");

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer jeton");
  });

  it("transforme le format d'erreur uniforme en ApiError", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(400, {
        detail: "Les données fournies sont invalides.",
        code: "validation_error",
        errors: { title: ["Le titre doit contenir au moins 8 caractères."] },
      }),
    );

    const error = (await api("/posts/", { method: "POST", body: {} }).catch((e: unknown) => e)) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("validation_error");
    expect(error.field("title")).toBe("Le titre doit contenir au moins 8 caractères.");
  });

  it("renouvelle la session une fois sur 401 puis rejoue la requête", async () => {
    setAccessToken("expiré");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { detail: "Jeton expiré", code: "token_not_valid" }))
      .mockResolvedValueOnce(jsonResponse(200, { access: "nouveau" }))
      .mockResolvedValueOnce(jsonResponse(200, { username: "awa" }));

    const body = await api<{ username: string }>("/auth/me/");

    expect(body.username).toBe("awa");
    expect(getAccessToken()).toBe("nouveau");
    expect(fetchMock.mock.calls[1][0]).toContain("/auth/token/refresh/");
    expect(fetchMock.mock.calls[1][1].credentials).toBe("include");
  });

  it("efface la session si le renouvellement échoue", async () => {
    setAccessToken("expiré");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { detail: "Jeton expiré", code: "token_not_valid" }))
      .mockResolvedValueOnce(jsonResponse(401, { detail: "Session expirée", code: "refresh_token_invalid" }));

    await expect(api("/auth/me/")).rejects.toMatchObject({ status: 401 });
    expect(getAccessToken()).toBeNull();
  });

  it("partage un seul renouvellement entre appels simultanés", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { access: "partagé" }));

    const results = await Promise.all([refreshSession(), refreshSession()]);

    expect(results).toEqual([true, true]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("signale une erreur réseau compréhensible", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(api("/posts/")).rejects.toMatchObject({ code: "network_error" });
  });

  it("gère les réponses 204 sans corps", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(api("/auth/logout/", { method: "POST" })).resolves.toBeUndefined();
  });
});
