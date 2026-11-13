# ADR 0001 — Authentification par JWT avec refresh token en cookie HttpOnly

- **Statut :** accepté
- **Date :** 2026-11-13
- **Exigences liées :** P0-01, module A, §10.3, §19 (point 4)

## Contexte

Le frontend Next.js est servi depuis une origine distincte de l'API. Le cahier des charges
(§10.3) autorise soit des sessions par cookie, soit des jetons à durée limitée, à condition de
ne jamais stocker un jeton sensible dans `localStorage` et de ne pas mélanger plusieurs
mécanismes.

## Décision

L'API utilise `djangorestframework-simplejwt` :

| Élément | Choix |
|---|---|
| Access token | JWT de 15 minutes (`JWT_ACCESS_MINUTES`), renvoyé dans le corps de la réponse, gardé **en mémoire** par le frontend et envoyé dans `Authorization: Bearer` |
| Refresh token | JWT de 7 jours (`JWT_REFRESH_DAYS`), posé dans un cookie `HttpOnly`, `Secure` en production, `SameSite` configurable, limité au chemin `/api/v1/auth/` |
| Rotation | chaque appel à `POST /auth/token/refresh/` révoque le refresh token présenté et en émet un nouveau |
| Révocation | liste noire (`token_blacklist`) ; `POST /auth/logout/` révoque le jeton et supprime le cookie |
| Changement / réinitialisation de mot de passe, désactivation | tous les refresh tokens du compte sont révoqués |

Le refresh token n'apparaît jamais dans un corps de réponse : il est inaccessible au
JavaScript, donc hors de portée d'une faille XSS.

### Protection CSRF des routes à cookie

Seules `token/refresh/` et `logout/` lisent le cookie. Elles sont protégées par :

1. `SameSite=Lax` par défaut (le cookie ne part pas sur un POST inter-sites) ;
2. un contrôle de l'en-tête `Origin` : s'il est présent, il doit figurer dans
   `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` (sinon `403 untrusted_origin`) ;
3. CORS restreint à `CORS_ALLOWED_ORIGINS` avec `CORS_ALLOW_CREDENTIALS=True` : une origine
   tierce ne peut pas lire l'access token renvoyé.

Toutes les autres routes s'authentifient par l'en-tête `Authorization`, qu'un site tiers ne peut
pas forger : elles ne sont pas exposées au CSRF.

### Déploiement inter-sites

Si le frontend et l'API ne partagent pas le même site enregistrable (ex. `app.vercel.app` et
`api.onrender.com`), régler `AUTH_COOKIE_SAMESITE=None` et `AUTH_COOKIE_SECURE=True`. Le contrôle
d'`Origin` reste alors la protection CSRF principale.

## Conséquences

- Le frontend doit appeler l'API avec `credentials: "include"` sur les routes `/auth/`.
- Un access token déjà émis reste valable jusqu'à son expiration (15 min au plus) après une
  déconnexion : c'est la contrepartie d'un jeton sans état. Un compte **désactivé** est en
  revanche rejeté immédiatement, car son état est relu à chaque requête.
- La connexion accepte l'e-mail ou le nom d'utilisateur ; le message d'erreur est identique dans
  tous les cas d'échec pour ne pas révéler l'existence d'un compte.
- La fermeture de compte est une **désactivation logique** (§19, point 6) : les contenus sont
  conservés, seul un administrateur peut réactiver le compte.

## Alternatives écartées

- **Sessions Django + CSRF token :** fiable sur un même domaine, mais plus fragile entre deux
  origines distinctes (cookies tiers, double cookie CSRF à synchroniser côté Next.js).
- **Access et refresh tokens dans `localStorage` :** exclu par le cahier des charges (vol par XSS).
