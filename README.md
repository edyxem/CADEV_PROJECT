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
│   ├── notifications/ # notifications internes
│   └── moderation/    # signalements, actions, journal d'audit
└── tests/             # scénarios de bout en bout
docs/                  # cahier des charges, ADR, guide API, modération
docker/                # Dockerfile, entrypoint
```

Décisions structurantes : [docs/adr/](docs/adr) (authentification, UUID, votes, suppression
logique, recherche).

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
| 16 autres membres | membre | annuaire varié (12 pays, mobile, data, cloud, sécurité…) |

Scénario jury (§17) rejouable intégralement via Swagger : connexion `awa_diop` → profil →
question « N+1 » et réponses → `GET /search/users/?technology=react` → connexion
`yao_kouassi` → demande sur CampusSecure → connexion `moussa_traore` → acceptation →
membres et attribution d'une tâche. Ce parcours est vérifié par
[`backend/tests/test_seed_demo.py`](backend/tests/test_seed_demo.py).

## Qualité

- 369 tests, couverture **96,8 %** (`apps/` + `common/`, seuil CI : 85 %).
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

Également livrés dès le P0 : réponses acceptées, notifications internes, profils privés.

### P1 et P2

Non commencés à ce stade (voir la feuille de route).

## Limites connues

- Pas d'envoi d'e-mails réels sans configuration SMTP (`EMAIL_BACKEND` console par défaut) :
  vérification d'adresse et réinitialisation fonctionnent, les liens s'affichent dans les
  journaux.
- Un access token déjà émis reste valable au plus 15 minutes après une déconnexion (compromis
  d'un jeton sans état) ; un compte désactivé est rejeté immédiatement.
- Les médias sont servis par Django en démonstration (`DJANGO_SERVE_MEDIA`) ; utiliser un
  stockage objet ou un serveur web en production.

## Feuille de route

- **P1** : favoris, abonnements et fil personnalisé, réputation et badges, jalons, mises à jour
  et fil d'activité de projet, tableau de bord, préférences de notification.
- **P2** : opportunités, mentorat, communautés, événements, messagerie privée,
  recommandations.
- **P3 (hors périmètre)** : OAuth GitHub, analyse de contributions, assistant IA, temps réel,
  application mobile, PWA hors ligne, traduction assistée, validation de compétences par
  tests, intégrations externes, statistiques avancées.

## Documentation

- [Guide d'intégration frontend](docs/api.md)
- [Modération](docs/moderation.md)
- [Décisions d'architecture](docs/adr)
