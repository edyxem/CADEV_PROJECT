# AfriDev Community — Backend

API REST de la plateforme communautaire et collaborative des développeurs africains
(CADEV 2026) : échanger, se connecter, construire.

`DISCUSSION → RENCONTRE → ÉQUIPE → PROJET → RÉALISATION → OPPORTUNITÉ`

Le backend Django est la source de vérité des règles métier ; il est consommé par un frontend
Next.js séparé. Spécification de référence : [docs/cahier_des_charges.md](docs/cahier_des_charges.md).

## Stack

| Couche | Choix |
|---|---|
| Langage | Python 3.12 |
| Framework | Django 5.2 LTS, Django REST Framework 3.18 |
| Base de données | PostgreSQL 16 (psycopg 3), recherche plein texte et trigrammes |
| Authentification | JWT SimpleJWT : access en mémoire, refresh en cookie `HttpOnly` (rotation + liste noire) |
| Documentation | drf-spectacular (OpenAPI 3, Swagger UI, ReDoc) |
| Sécurité contenu | nh3 (HTML en liste blanche), Pillow (contrôle et réencodage des images) |
| Exécution | Gunicorn, WhiteNoise, Docker multi-étapes (utilisateur non-root) |
| Qualité | pytest, pytest-django, factory_boy, ruff, pre-commit, GitHub Actions |

Toutes les versions sont figées dans [`requirements/`](requirements).

## Architecture

Monolithe modulaire (§6.1) : une app Django par domaine, logique métier dans `services.py`,
lectures complexes dans `selectors.py`, vues fines.

```
backend/
├── config/            # settings base / dev / test / prod, routes
├── common/            # BaseModel UUID, erreurs, pagination, permissions, throttling,
│                      # assainissement, validateurs, images, données de démo
├── apps/
│   ├── accounts/      # utilisateur personnalisé, rôles globaux, auth JWT, mots de passe
│   ├── profiles/      # profil développeur, compétences, liens, annuaire
│   ├── catalog/       # catégories, tags, technologies, pays
│   ├── community/     # publications, commentaires, réponses, votes
│   ├── search/        # recherche PostgreSQL (fr sans accents + trigrammes)
│   ├── projects/      # projets, équipe, rôles recherchés, demandes, tâches
│   ├── notifications/ # notifications internes et préférences
│   ├── social/        # abonnements et fil personnalisé
│   ├── reputation/    # contributions, badges, recommandations, tableau de bord
│   ├── opportunities/ # opportunités, organisations vérifiées (P2)
│   ├── mentorship/    # mentors, demandes, sessions, retours (P2)
│   ├── communities/   # communautés thématiques et géographiques (P2)
│   ├── events/        # agenda, inscriptions, rappels (P2)
│   ├── messaging/     # messagerie privée, blocage (P2)
│   └── moderation/    # signalements, actions, journal d'audit
└── tests/             # scénarios de bout en bout
docs/                  # cahier des charges, ADR, guide API, modération
docker/                # Dockerfile, entrypoint
```

Décisions structurantes : [docs/adr/](docs/adr) (authentification, UUID, votes, suppression
logique, recherche, extensions P2).

## Démarrage rapide (Docker)

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python manage.py seed_demo
```

- API : http://localhost:8000/api/v1/
- Swagger : http://localhost:8000/api/docs/ — ReDoc : http://localhost:8000/api/redoc/
- Santé : http://localhost:8000/api/v1/health/
- Admin Django : http://localhost:8000/admin/ (compte `demo_admin`)

Le conteneur attend PostgreSQL, applique les migrations, collecte les fichiers statiques et
charge les référentiels (`SEED_REFERENCE=1`). `SEED_DEMO=1` charge aussi la démo au démarrage.

> Le `docker-compose.yml` sert la démonstration locale en HTTP (`DJANGO_SECURE_SSL_REDIRECT`,
> HSTS et cookies `Secure` désactivés par variables). En déploiement réel, placer l'API derrière
> un proxy HTTPS et laisser ces réglages à leur valeur par défaut.

## Développement local (sans Docker pour l'API)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements/dev.txt
cp .env.example .env
docker compose up -d db          # PostgreSQL sur le port 5434
python backend/manage.py migrate
python backend/manage.py seed_demo
python backend/manage.py runserver
pre-commit install
```

## Commandes

| Commande | Effet |
|---|---|
| `make up` / `make down` | démarre / arrête la pile Docker |
| `make migrate` | applique les migrations |
| `make seed` | données de démonstration fictives (idempotent) |
| `make seed-reference` | référentiels seuls (utilisable en production) |
| `make test` | tests avec couverture |
| `make lint` | ruff (lint + format) et contrôle des migrations |
| `make check` | `check --deploy` avec les settings de production |
| `python backend/manage.py rebuild_search_index` | reconstruit l'index de recherche |
| `python backend/manage.py recompute_reputation` | recalcule réputations et badges |
| `python backend/manage.py send_event_reminders` | rappels d'événements (à planifier via cron) |

## Variables d'environnement

Voir [.env.example](.env.example) (aucun secret réel n'est versionné). Principales :

| Variable | Rôle |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` / `prod` |
| `DJANGO_SECRET_KEY` | obligatoire en production |
| `DJANGO_ALLOWED_HOSTS` | obligatoire en production |
| `DATABASE_URL` | connexion PostgreSQL |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | origine(s) du frontend |
| `FRONTEND_URL` | liens envoyés par e-mail |
| `AUTH_COOKIE_SAMESITE`, `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_DOMAIN` | cookie de session |
| `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS` | durées des jetons |
| `EMAIL_*` | envoi d'e-mails (console par défaut) |
| `THROTTLE_*` | limites de débit |

## Comptes de démonstration

Tous fictifs, mot de passe commun **`Demo-AfriDev-2026`** (démonstration uniquement).

| Compte | Rôle | Utilité dans la démo |
|---|---|---|
| `demo_admin` | administrateur | admin Django, restauration, bannissement, journal d'audit |
| `demo_moderateur` | modérateur | file des signalements (3 signalements de test) |
| `awa_diop` | membre | profil complet, question avec réponse acceptée, propriétaire d'AgriMarché |
| `kofi_mensah` | membre | développeur React, membre d'AgriMarché |
| `moussa_traore` | membre | propriétaire de CampusSecure (demandes en attente) |
| `yao_kouassi` | membre | candidat idéal pour rejoindre CampusSecure pendant la démo |
| `chinedu_okafor` | membre | organisation vérifiée, opportunités publiées, mentor |
| `kwame_asante` | membre | mentor ayant accepté un mentorat (session planifiée) |
| `fatou_ndiaye` | membre | mentorée, membre de la communauté « Développeurs de Dakar », inscrite à un atelier |
| 13 autres membres | membre | annuaire varié (14 pays, mobile, data, cloud, sécurité…) |

Scénario jury (§17) rejouable intégralement via Swagger : connexion `awa_diop` → profil →
question « N+1 » et réponses → `GET /search/users/?technology=react` → connexion
`yao_kouassi` → demande sur CampusSecure → connexion `moussa_traore` → acceptation →
membres et attribution d'une tâche. Ce parcours est vérifié par
[`backend/tests/test_seed_demo.py`](backend/tests/test_seed_demo.py).

## Qualité

- 489 tests, couverture **97 %** (`apps/` + `common/`, seuil CI : 85 %).
- Permissions testées par rôle (anonyme, membre, auteur, autre membre, rôles projet,
  modérateur, administrateur), IDOR, non-fuite des champs privés, transitions interdites,
  limites de débit.
- Scénario de bout en bout du §12.3 rejoué via l'API :
  [`backend/tests/test_e2e_scenario.py`](backend/tests/test_e2e_scenario.py).
- CI : ruff, migrations à jour, `check --deploy`, schéma OpenAPI sans avertissement, tests et
  couverture, construction de l'image Docker.

## Couverture des exigences

### P0 — MVP

| ID | Exigence | Statut | Où |
|---|---|---|---|
| P0-01 | Inscription, connexion, déconnexion, récupération | Fait | `accounts` |
| P0-02 | Profils développeurs | Fait | `profiles` |
| P0-03 | Fil communautaire et catégories | Fait | `community` |
| P0-04 | Publications (création, modification, suppression logique) | Fait | `community` |
| P0-05 | Commentaires et réponses | Fait | `community` |
| P0-06 | Votes uniques | Fait | `community` |
| P0-07 | Catégories et technologies | Fait | `catalog` |
| P0-08 | Recherche et filtres | Fait | `search` |
| P0-09 | Appels à collaboration | Fait | `projects` |
| P0-10 | Demandes pour rejoindre | Fait | `projects` |
| P0-11 | Espace projet (membres, rôles, dépôt, tâches, statut) | Fait | `projects` |
| P0-12 | Signalement et traitement | Fait | `moderation` |
| P0-13 | Administration minimale | Fait | Django Admin + `moderation` |
| P0-14 | Interface responsive | Hors périmètre backend | frontend |


### P1 — Fonctions importantes

| Fonction | Statut | Où |
|---|---|---|
| Profils enrichis (projets, contributions, disponibilité détaillée) | Fait | `profiles`, `reputation` |
| Filtres avancés de découverte de développeurs | Fait | `profiles`, `search` |
| Articles / tutoriels avec mise en forme | Fait (HTML assaini) | `community` |
| Réponses acceptées | Fait | `community` |
| Favoris | Fait | `community` |
| Abonnements (membres, technologies, catégories) et fil personnalisé | Fait | `social` |
| Notifications internes | Fait | `notifications` |
| Tâches avancées : échéances, jalons, commentaires, Kanban | Fait | `projects` |
| Mises à jour de projet et fil d'activité / historique | Fait | `projects` |
| Invitations directes et gestion avancée des rôles | Fait | `projects` |
| Pièces jointes de projet | Non fait | — |
| Badges et réputation fondés sur des actions réelles | Fait | `reputation` ([règles](docs/reputation.md)) |
| Tableau de bord utilisateur | Fait | `GET /me/dashboard/` |
| Profil privé / public et paramètres de notification | Fait | `profiles`, `notifications` |
| Interface anglaise préparée | Partiel : `LocaleMiddleware` et `LANGUAGES` en place, messages encore en français uniquement | `config` |

### P2 — Extensions

| Fonction | Statut | Où |
|---|---|---|
| Annuaire d'opportunités (emplois, stages, freelance, bourses, hackathons…) | Fait | `opportunities` |
| Candidatures / demandes d'information | Fait (sans recrutement de bout en bout) | `opportunities` |
| Pages d'organisation et partenaires vérifiés | Fait (vérification par un admin) | `opportunities` |
| Mentorat : profils, demandes, sessions, retours | Fait | `mentorship` |
| Communautés par pays, ville, université, technologie, domaine | Fait | `communities` |
| Événements, agenda, inscriptions, rappels | Fait (rappels par commande planifiable) | `events` |
| Messagerie privée, blocage, signalement | Fait (sans temps réel) | `messaging` |
| Recommandations de développeurs et de projets | Fait (recouvrement de technologies, explicable) | `social` |
| Portfolio enrichi de réalisations | Fait | `profiles` |
| Notifications par e-mail | Fait (types choisis, adresse vérifiée, SMTP à configurer) | `notifications` |

Choix et limites : [ADR 0006](docs/adr/0006-extensions-p2.md).

## Limites connues

- Pas d'envoi d'e-mails réels sans configuration SMTP (`EMAIL_BACKEND` console par défaut) :
  vérification d'adresse et réinitialisation fonctionnent, les liens s'affichent dans les
  journaux.
- Un access token déjà émis reste valable au plus 15 minutes après une déconnexion (compromis
  d'un jeton sans état) ; un compte désactivé est rejeté immédiatement.
- Les médias sont servis par Django en démonstration (`DJANGO_SERVE_MEDIA`) ; utiliser un
  stockage objet ou un serveur web en production.
- Les messages d'erreur de l'API sont en français uniquement ; l'infrastructure i18n est en
  place mais les traductions ne sont pas faites.
- Pas de temps réel : notifications et messagerie se rafraîchissent par interrogation.
- Les rappels d'événements nécessitent de planifier `send_event_reminders` (cron) ;
  aucun ordonnanceur n'est fourni dans `docker-compose.yml`.
- La réputation est recalculée après chaque transaction concernée ; à forte charge, un
  recalcul différé (file de tâches) serait préférable.
- La CI GitHub Actions a été reproduite localement (lint, migrations, `check --deploy`,
  schéma, tests, image) ; son exécution sur GitHub est à confirmer au premier push.

## Feuille de route

- **Reste à faire (P1)** : traduction anglaise des messages, pièces jointes de projet.
- **P3 (hors périmètre)** : OAuth GitHub, analyse de contributions, assistant IA, temps réel,
  application mobile, PWA hors ligne, traduction assistée, validation de compétences par
  tests, intégrations externes, statistiques avancées.

## Documentation

- [Guide d'intégration frontend](docs/api.md)
- [Modération](docs/moderation.md)
- [Réputation et badges](docs/reputation.md)
- [Décisions d'architecture](docs/adr)
