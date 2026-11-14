# Guide d'intégration de l'API — équipe frontend

Référence complète et à jour : **Swagger UI** `/api/docs/`, **ReDoc** `/api/redoc/`, schéma
OpenAPI 3 `/api/schema/` (utilisable pour générer un client TypeScript, par exemple avec
`openapi-typescript`).

- Base : `http://localhost:8000/api/v1/` (variable `NEXT_PUBLIC_API_BASE_URL`).
- JSON en entrée et en sortie (sauf téléversement d'images en `multipart/form-data`).
- Dates en ISO 8601, en UTC (`2026-11-13T10:30:00Z`) : à convertir dans le fuseau de
  l'utilisateur à l'affichage.
- Identifiants : UUID. Projets, catégories, technologies et tags sont aussi adressables par
  `slug`, les profils par `username`, les pays par code ISO (`SN`, `CI`…).

## 1. Authentification

Voir [ADR 0001](adr/0001-authentification.md).

| Étape | Appel | Résultat |
|---|---|---|
| Inscription | `POST /auth/register/` `{username, email, password}` | `201 {access, user}` + cookie |
| Connexion | `POST /auth/login/` `{identifier, password}` (e-mail **ou** nom d'utilisateur) | `200 {access, user}` + cookie |
| Appels authentifiés | en-tête `Authorization: Bearer <access>` | — |
| Renouvellement | `POST /auth/token/refresh/` sans corps | `200 {access}` + nouveau cookie |
| Déconnexion | `POST /auth/logout/` | `204`, cookie supprimé |
| Compte courant | `GET /auth/me/` | e-mail, rôle global, état |

- L'**access token** (15 min) se garde **en mémoire** (état React, jamais `localStorage`).
- Le **refresh token** (7 j) est dans le cookie `HttpOnly` `afridev_refresh`, limité au chemin
  `/api/v1/auth/` : le JavaScript n'y a pas accès.
- Les appels `/auth/token/refresh/` et `/auth/logout/` doivent être faits avec
  `credentials: "include"` depuis une origine listée dans `CORS_ALLOWED_ORIGINS`.

Exemple de client minimal :

```ts
let accessToken: string | null = null;

async function api(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init.headers,
    },
  });
  if (response.status === 401 && retry) {
    const refreshed = await fetch(`${API}/auth/token/refresh/`, { method: "POST", credentials: "include" });
    if (refreshed.ok) {
      accessToken = (await refreshed.json()).access;
      return api(path, init, false);
    }
    accessToken = null; // session expirée : rediriger vers /connexion
  }
  return response;
}
```

Au chargement de l'application, appeler `POST /auth/token/refresh/` pour restaurer la session.

Codes particuliers : `invalid_credentials` (401), `account_suspended` (403, mot de passe
correct mais compte suspendu), `refresh_token_missing` / `refresh_token_invalid` (401),
`untrusted_origin` (403).

## 2. Pagination

Toutes les listes suivent la même convention :

```json
{ "count": 42, "next": "…?page=3", "previous": "…?page=1", "results": [ … ] }
```

Paramètres : `page` (1 par défaut), `page_size` (20 par défaut, **100 au maximum**).

## 3. Erreurs

Format unique :

```json
{ "detail": "Les données fournies sont invalides.", "code": "validation_error",
  "errors": { "title": ["Le titre doit contenir au moins 8 caractères."] } }
```

| Statut | Signification | Que faire côté UI |
|---|---|---|
| 400 | `validation_error` : `errors` donne les messages par champ | afficher sous chaque champ |
| 401 | non authentifié / jeton expiré | tenter un refresh, sinon connexion |
| 403 | permission insuffisante | masquer l'action, message neutre |
| 404 | introuvable **ou non visible** (contenu masqué, projet privé) | page « indisponible » |
| 409 | règle métier : `code` précise (`duplicate_request`, `self_vote`, `invalid_transition`, `project_closed`…) | message dédié |
| 429 | limite de débit | réessayer plus tard, éviter les doubles clics |

Les messages sont en français et peuvent être affichés tels quels.

## 4. Parcours principaux

### Fil et publications

- Fil : `GET /posts/?ordering=recent|active|popular|unanswered&type=&category=&technology=&tag=&q=`
- Publier : `POST /posts/` `{type, title, content, category, tags[], technologies[], status}`
  (`type` : `DISCUSSION`, `QUESTION`, `ARTICLE` ; `ANNOUNCEMENT` réservé à la modération ;
  `status: DRAFT` pour un brouillon).
- Le contenu accepte un HTML limité (`p, a, strong, em, code, pre, ul, ol, li, blockquote,
  h2–h4, br, hr`). Tout le reste est supprimé côté serveur. Les compteurs
  (`vote_count`, `comment_count`, `answer_count`) et `has_voted` sont calculés par l'API.
- Modifier / supprimer : `PATCH|DELETE /posts/{id}/` (auteur ; `can_edit` l'indique).
- Commentaires : `GET|POST /posts/{id}/comments/` (`parent` pour répondre, un seul niveau).
  Un commentaire retiré qui a des réponses revient avec `is_removed: true`.
- Vote : `POST /posts/{id}/vote/` (bascule) ou `{active: true|false}` (idempotent) ;
  `DELETE` retire. Réponse : `{voted, vote_count}`.

### Questions et réponses

- `GET /questions/`, `GET|POST /questions/{id}/answers/` (acceptée d'abord, puis votes).
- `POST /answers/{id}/vote/`, `POST|DELETE /answers/{id}/accept/` (auteur de la question,
  jamais sa propre réponse).

### Profils et annuaire

- `GET /profiles/?technology=&country=&domain=&availability=&level=&language=&city=&q=`
- `GET /profiles/{username}/` : un profil privé renvoie `{username, display_name, avatar,
  is_private: true}` aux autres membres.
- `GET|PATCH /profiles/me/`, `GET|PUT|PATCH /profiles/me/skills/`,
  `/profiles/me/links/`, `PUT|DELETE /profiles/me/avatar/` (multipart, champ `avatar`).
- `show_city`, `show_availability` et `show_reputation` (score, badges, recommandations)
  masquent ces éléments aux autres membres ; le titulaire les voit toujours.
- Projets d'un membre : `GET /projects/?member={username}`.
- La recherche par auteur (`author=`) ne renvoie que les auteurs au profil public.
- Une compétence affiche `verification_label` ; `is_verified` n'est vrai qu'après validation
  par des pairs (jamais pour un simple lien).

### Projets et collaboration

1. `POST /projects/` → le créateur devient `OWNER`.
2. `POST /projects/{slug}/roles/` → rôles recherchés.
3. Candidat : `POST /projects/{slug}/join-requests/` `{message, requested_role?}` ;
   suivi par `GET /join-requests/mine/`, retrait par `POST /join-requests/{id}/withdraw/`.
4. Propriétaire / responsable habilité : `GET /projects/{slug}/join-requests/`, puis
   `POST /join-requests/{id}/accept/` `{role, response_message}` ou `/reject/`.
5. Équipe : `GET /projects/{slug}/members/`, `PATCH|DELETE …/members/{id}/`,
   `POST /projects/{slug}/leave/`, `POST /projects/{slug}/transfer-ownership/`.
6. Tâches (membres) : `GET|POST /projects/{slug}/tasks/?status=&assignee=me`,
   `PATCH|DELETE /tasks/{id}/`.

Le détail d'un projet renvoie `my_role` et `permissions` (`edit_settings`, `manage_members`,
`manage_tasks`, `create_tasks`, `view_tasks`) : à utiliser pour afficher ou masquer les
actions. Le serveur revérifie toujours.

### Recherche

`GET /search/?q=` (aperçu : posts, users, projects), puis `/search/posts/`, `/search/users/`,
`/search/projects/` paginés, combinables avec les filtres des listes.

### Notifications

`GET /notifications/?is_read=false`, `GET /notifications/unread-count/`,
`POST /notifications/{id}/read/`, `POST /notifications/read-all/`. `target_url` est un chemin
frontend relatif (ex. `/publications/<id>`, `/projets/<slug>`).

### Signalement et modération

- Membre : `POST /reports/` `{target_type, target_id, reason, details}`.
- Modération : `GET /moderation/reports/`, `POST …/{id}/claim/`, `POST …/{id}/action/`
  `{action, reason, duration_days?}`, `POST …/{id}/close/`, `POST /moderation/actions/`,
  `GET /moderation/stats/` ; administrateurs : `GET /moderation/audit-logs/`.
  Voir [moderation.md](moderation.md).

## 5. Limites de débit par défaut

| Périmètre | Limite |
|---|---|
| Connexion / refresh | 10 / min |
| Inscription | 10 / h |
| Mot de passe, e-mail | 5 / h |
| Publication, réponse | 30 / h |
| Commentaire | 60 / h |
| Signalement | 20 / h |
| Demande pour rejoindre | 20 / h |
| Recherche | 60 / min |
| Global (anonyme / connecté) | 120 / 300 par min |

## 6. Fonctions P1 et P2

| Domaine | Endpoints principaux |
|---|---|
| Favoris | `POST|DELETE /posts/{id}/bookmark/`, `GET /posts/bookmarks/` |
| Abonnements | `GET|POST /follows/` `{target_type: USER|TECHNOLOGY|CATEGORY, target}`, `DELETE /follows/{id}/`, `GET /follows/followers/`, `GET /profiles/{username}/follow-stats/` |
| Fil personnalisé | `GET /feed/` (le fil général `/posts/` reste disponible) |
| Préférences | `GET|PATCH /notifications/preferences/` `{muted_types, email_types}` |
| Réputation | `GET /profiles/{username}/reputation/`, `GET /achievements/`, `GET|POST /profiles/{username}/recommendations/` — voir [reputation.md](reputation.md) |
| Tableau de bord | `GET /me/dashboard/` |
| Suivi de projet | `…/projects/{slug}/milestones/`, `…/updates/`, `…/activity/`, `…/board/`, `…/invitations/`, `GET|POST /tasks/{id}/comments/`, `/invitations/{id}/accept|decline|cancel/` |
| Opportunités | `GET|POST /opportunities/?type=&country=&work_mode=&technology=&include_expired=`, `POST /opportunities/{id}/submit/`, `GET|POST /opportunities/{id}/interests/`, modération : `GET /opportunities/review-queue/`, `POST /opportunities/{id}/review/` |
| Organisations | `GET|POST /organizations/`, `POST /organizations/{slug}/verify/` (admin) |
| Mentorat | `GET /mentors/`, `GET|PUT /mentors/me/`, `GET|POST /mentorship-requests/`, `…/{id}/respond|cancel|complete/`, `…/{id}/sessions/`, `PATCH /mentorship-sessions/{id}/`, `…/{id}/feedback/` |
| Communautés | `GET|POST /communities/`, `…/{slug}/join|leave/`, `…/members/`, `…/posts/`, `…/posts/{id}/moderate/` ; publier : `POST /posts/` avec `community` |
| Événements | `GET /events/?when=upcoming|past|all`, `POST /events/`, `…/{id}/register/` (POST/DELETE), `…/{id}/cancel/`, `…/{id}/registrations/`, `GET /events/mine/` |
| Messagerie | `GET|POST /conversations/` `{username, content}`, `GET|POST /conversations/{id}/messages/`, `POST /conversations/{id}/read/`, `GET|POST /blocks/`, `DELETE /blocks/{id}/` |
| Découverte | `GET /recommendations/developers/`, `GET /recommendations/projects/` |
| Portfolio | `GET|POST /profiles/me/portfolio/`, `GET /profiles/{username}/portfolio/` |

Pas de temps réel : rafraîchir périodiquement `GET /notifications/unread-count/` et la liste des
conversations (par exemple toutes les 30 à 60 secondes, ou au retour de focus de l'onglet).
