# AfriDev Community — Guide d'utilisation

Ce guide explique comment installer la plateforme, ce qui est déjà disponible et comment
réaliser chaque action, que vous soyez membre, modérateur, administrateur ou développeur
du projet.

**Sommaire**

1. Installer et lancer la plateforme
2. Ce qui est déjà fait
3. Guide du membre : comment faire quoi
4. Guide du modérateur
5. Guide de l'administrateur
6. Guide du développeur
7. Dépannage
8. Limites connues

---

## 1. Installer et lancer la plateforme

### 1.1 Prérequis

- **Docker Desktop** installé et démarré (Windows, macOS ou Linux).
- Les ports **3000** (site), **8000** (API et administration) et **5434** (base de données)
  libres.
- Pour développer sans Docker : Python 3.12 et Node.js 22.

### 1.2 Premier lancement (une seule fois)

Depuis le dossier du projet :

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend python manage.py seed_demo
```

1. `cp .env.example .env` crée la configuration locale (les valeurs par défaut suffisent).
2. `docker compose up --build -d` construit et démarre trois services : la base PostgreSQL,
   l'API Django et le site Next.js. Le premier lancement prend quelques minutes.
3. `seed_demo` charge des données de démonstration **fictives** : membres, publications,
   projets, opportunités, événements, communautés, mentors, signalements.

### 1.3 Adresses utiles

| Adresse | Contenu |
|---|---|
| http://localhost:3000 | Le site AfriDev Community |
| http://localhost:8000/admin/ | L'administration |
| http://localhost:8000/api/docs/ | La documentation interactive de l'API (Swagger) |
| http://localhost:8000/api/v1/health/ | L'état de santé de l'API |

### 1.4 Comptes de démonstration

Mot de passe commun : **`Demo-AfriDev-2026`** (comptes fictifs, démonstration uniquement).

| Compte | Rôle | À utiliser pour |
|---|---|---|
| `awa_diop` | membre | Parcours principal : profil complet, question résolue, propriétaire du projet AgriMarché |
| `kofi_mensah` | membre | Développeur React, membre d'AgriMarché, conversation avec Awa |
| `yao_kouassi` | membre | Demander à rejoindre le projet CampusSecure |
| `moussa_traore` | membre | Propriétaire de CampusSecure : accepter les demandes |
| `chinedu_okafor` | membre | Organisation vérifiée, opportunités publiées, mentor |
| `kwame_asante` | membre | Mentor ayant accepté un mentorat |
| `fatou_ndiaye` | membre | Mentorée, membre d'une communauté, inscrite à un atelier |
| `demo_moderateur` | modérateur | File de modération (3 signalements de test) |
| `demo_admin` | administrateur | Administration complète |

### 1.5 Arrêter, relancer, réinitialiser

| Action | Commande |
|---|---|
| Arrêter (les données sont conservées) | `docker compose down` |
| Relancer | `docker compose up -d` |
| Voir les journaux de l'API | `docker compose logs -f backend` |
| Repartir de zéro (efface la base) | `docker compose down -v`, puis les commandes du §1.2 |

---

## 2. Ce qui est déjà fait

Légende : ✅ disponible · 🟡 disponible via l'administration ou l'API seulement · ❌ non livré

### 2.1 Comptes et profils

| Fonction | Site web | Remarque |
|---|---|---|
| Inscription, connexion, déconnexion | ✅ | Connexion par e-mail ou nom d'utilisateur |
| Mot de passe oublié et réinitialisation | ✅ | Lien envoyé par e-mail |
| Vérification et changement d'adresse e-mail | ✅ | Lien envoyé par e-mail |
| Profil développeur : titre, bio, pays, ville, niveau, disponibilité | ✅ | Page « Paramètres du profil » |
| Compétences (technologie + niveau) | ✅ | |
| Profil public ou privé | ✅ | |
| Portfolio de réalisations | 🟡 | API `profiles/me/portfolio/` |

### 2.2 Communauté

| Fonction | Site web | Remarque |
|---|---|---|
| Fil communautaire avec filtres (type, catégorie, technologie) | ✅ | |
| Questions et réponses, réponse acceptée | ✅ | |
| Discussions, articles, annonces | ✅ | |
| Commentaires, votes, favoris | ✅ | Un seul vote par personne |
| Recherche plein texte | ✅ | En français, insensible aux accents |
| Signalement de contenus | ✅ | Sur publications, profils, projets, messages, annonces, événements |
| Abonnements et fil personnalisé | 🟡 | API `follows/` et `feed/` |

### 2.3 Réseau et projets

| Fonction | Site web | Remarque |
|---|---|---|
| Annuaire des développeurs avec filtres | ✅ | Technologie, pays, disponibilité, niveau |
| Messagerie privée, blocage | ✅ | Rafraîchissement automatique toutes les 15 s |
| Création de projet et rôles recherchés | ✅ | |
| Demandes pour rejoindre, acceptation, refus | ✅ | |
| Tableau de tâches en glisser-déposer | ✅ | |
| Jalons, mises à jour, invitations, commentaires de tâches | 🟡 | API `projects/{slug}/…` |
| Pièces jointes de projet | ❌ | Prévu |

### 2.4 Opportunités, événements, communautés, mentorat

| Fonction | Site web | Remarque |
|---|---|---|
| Consulter et filtrer les opportunités | ✅ | Type, mode de travail, technologie, pays |
| Candidater ou demander des informations | ✅ | L'auteur de l'annonce est notifié |
| Publier une opportunité | 🟡 | API `opportunities/` ; relue par la modération avant publication |
| Valider une opportunité | 🟡 | Administration (actions « Publier » / « Refuser ») ou API |
| Agenda des événements, inscription et désinscription | ✅ | |
| Créer un événement | 🟡 | Administration ou API `events/` |
| Communautés : rejoindre, quitter, publier, fil | ✅ | |
| Créer une communauté | 🟡 | Administration ou API `communities/` |
| Mentors : consulter, demander, accepter, terminer | ✅ | |
| Devenir mentor | 🟡 | API `mentors/me/` ou administration |
| Sessions et retours de mentorat | 🟡 | API `mentorship-requests/{id}/sessions/` |

### 2.5 Suivi, modération, administration

| Fonction | Site web | Remarque |
|---|---|---|
| Notifications internes | ✅ | Compteur rafraîchi toutes les 60 s |
| Tableau de bord personnel et recommandations | ✅ | Page « Tableau de bord » |
| Réputation et badges | ✅ | Visibles sur le profil public |
| File de modération et décisions | ✅ | Réservé aux modérateurs |
| Administration avec indicateurs en direct | ✅ | `/admin/` |
| Journal d'audit | ✅ | Administration, en lecture seule |
| Notifications par e-mail | 🟡 | Nécessite un serveur SMTP |
| Interface en anglais | ❌ | Préparée, non traduite |

---

## 3. Guide du membre : comment faire quoi

### 3.1 Créer un compte et se connecter

1. Cliquez sur **Rejoindre** en haut à droite.
2. Choisissez un nom d'utilisateur, saisissez votre e-mail et un mot de passe solide.
3. Vous êtes connecté automatiquement. Pour revenir plus tard : **Connexion**, puis votre
   e-mail **ou** votre nom d'utilisateur.

La session reste ouverte quelques jours sur votre navigateur. **Se déconnecter** se trouve
sous la barre de navigation (ou dans le menu ☰ sur mobile).

### 3.2 J'ai oublié mon mot de passe

1. Sur la page **Connexion**, cliquez sur **Mot de passe oublié ?**.
2. Saisissez votre adresse e-mail, puis **Envoyer le lien**.
3. Ouvrez le lien reçu par e-mail et choisissez un nouveau mot de passe.

> En démonstration locale, aucun e-mail n'est réellement envoyé : le lien apparaît dans les
> journaux (voir §7).

### 3.3 Vérifier mon adresse e-mail

Si votre adresse n'est pas vérifiée, un bandeau ocre apparaît sur votre **Tableau de bord**.
Cliquez sur **Renvoyer le lien**, puis ouvrez le lien reçu.

### 3.4 Compléter mon profil

1. Cliquez sur **Paramètres du profil**.
2. Renseignez votre nom d'affichage, titre, biographie, pays, ville, niveau et disponibilité.
3. Choisissez la **visibilité** : *Public* (visible dans l'annuaire) ou *Privé*.
4. Ajoutez vos **compétences** : une technologie et un niveau, puis **Ajouter**.

Votre profil public est accessible en cliquant sur votre avatar.

### 3.5 Poser une question ou publier

1. Cliquez sur **+ Publier**.
2. Choisissez le type : *Question*, *Discussion*, *Article* ou *Annonce*.
3. Donnez un titre précis, une catégorie, le contenu et les technologies concernées.
   Pour une question, décrivez aussi votre environnement (versions, système).
4. **Publier**, ou **Enregistrer en brouillon** pour terminer plus tard.

### 3.6 Répondre, commenter, voter, mettre en favori

Ouvrez une publication depuis le **Fil** ou **Questions** :

- **▲** pour voter (une fois par publication ; cliquez à nouveau pour retirer le vote) ;
- **☆** pour l'ajouter à vos favoris ;
- le formulaire en bas pour **répondre** (question) ou **commenter** ;
- si vous êtes l'auteur d'une question, **Accepter cette réponse** sur celle qui vous a aidé.

### 3.7 Rechercher

- Publications : barre de recherche du **Fil** ou de **Questions**, avec filtres.
- Développeurs : page **Développeurs**, recherche et filtres (technologie, pays, disponibilité,
  niveau).
- Projets : page **Projets**, recherche et filtres (recrutement, technologie, statut).

### 3.8 Contacter un développeur

- Depuis son profil : **Envoyer un message**.
- Ou icône 💬 **Messages** → **Nouvelle conversation** → nom d'utilisateur et message.

Dans une conversation, **Entrée** envoie le message et **Maj + Entrée** ajoute un retour à la
ligne. **Bloquer** empêche un membre de vous écrire ; un message inapproprié peut être signalé
en le survolant.

### 3.9 Lancer un projet et constituer une équipe

1. **Projets** → **Créer un projet** : nom, résumé, problématique, objectifs, description,
   mode de collaboration, disponibilité attendue, liens du dépôt et de la démonstration.
2. Sur la page du projet, ajoutez les **rôles recherchés** (par exemple « Développeur·se
   frontend », nombre de places).
3. Les candidats envoient une demande : vous êtes notifié. Ouvrez **Demandes** pour les
   **accepter** ou les **refuser** (lien **Demandes reçues** sur la page du projet).

### 3.10 Rejoindre un projet

1. Ouvrez un projet qui recrute (point vert pulsant).
2. Dans **Rejoindre l'équipe**, choisissez le rôle visé et expliquez votre motivation
   (20 caractères minimum).
3. **Envoyer ma demande**. Vous serez notifié de la réponse.

### 3.11 Organiser les tâches

1. Sur la page du projet, ouvrez **Tâches du projet** (réservé aux membres).
2. Créez une tâche : titre, personne assignée, priorité.
3. **Glissez** une carte vers une autre colonne (*À faire*, *En cours*, *En revue*,
   *Terminée*, *Bloquée*), ou utilisez le sélecteur de statut sous la carte.

Certains passages sont interdits (par exemple *À faire* → *En revue* directement) : la carte
revient alors à sa place et un message l'explique. Seuls la personne assignée et les
responsables peuvent terminer une tâche.

### 3.12 Trouver une opportunité et candidater

1. Menu **Explorer** → **Opportunités**.
2. Filtrez par type (emploi, stage, bourse, hackathon…), mode de travail, technologie ou pays.
   Le badge **✓ Partenaire vérifié** signale une organisation contrôlée par l'équipe.
3. Ouvrez l'annonce, puis dans **Manifester mon intérêt** : *Candidater* ou *Demander des
   informations*, avec un court message. L'auteur est notifié.

### 3.13 Participer à un événement

**Explorer** → **Événements** → onglet *À venir* → **S'inscrire**. Retrouvez vos inscriptions
dans l'onglet **Mes inscriptions**. Pour un événement en ligne, le lien de connexion apparaît
sur la page de l'événement une fois inscrit.

### 3.14 Rejoindre une communauté

**Explorer** → **Communautés** → filtrez par type (pays, ville, université, technologie,
domaine) → **Rejoindre**. Sur la page de la communauté, **Publier dans cette communauté**
crée une publication rattachée à celle-ci.

### 3.15 Être accompagné par un mentor

1. **Explorer** → **Mentorat**.
2. Choisissez un mentor disponible → **Demander un accompagnement** → décrivez votre objectif
   (30 caractères minimum).
3. Suivez l'état de votre demande dans **Mes demandes**. Une fois acceptée : **Écrire un
   message** au mentor, puis **Marquer comme terminé** à la fin de l'accompagnement.

Si vous êtes mentor, les demandes reçues apparaissent en haut de la page : **Accepter** ou
**Décliner**.

### 3.16 Suivre mon activité

- 🔔 **Notifications** : réponses, votes, demandes, décisions, messages. Cliquez pour ouvrir
  la page concernée ; **Tout marquer comme lu**.
- **Tableau de bord** : réputation, publications, réponses, projets, tâches ouvertes, demandes
  à examiner, abonnés, et des **recommandations** de développeurs et de projets.

### 3.17 Signaler un contenu

Bouton **Signaler** sur une publication, un profil, un projet, une annonce, un événement ou un
message → choisissez le motif → envoyez. La modération traite le signalement ; l'auteur du
signalement n'est jamais révélé.

---

## 4. Guide du modérateur

Connectez-vous avec un compte modérateur (démo : `demo_moderateur`). Le lien **Modération**
apparaît dans la navigation.

1. **Modération** affiche les signalements ouverts, du plus ancien au plus récent, avec un
   aperçu du contenu.
2. Choisissez une **décision** :
   - *Rejeter (aucune action)* ;
   - *Avertir l'auteur* ;
   - *Masquer le contenu* ;
   - *Supprimer le contenu* ;
   - *Suspendre le compte* (durée de 1 à 90 jours).
3. Saisissez le **motif** (il est journalisé et communiqué au membre), puis **Appliquer la
   décision**.

Les annonces d'opportunités en attente se valident via l'API
(`POST /api/v1/opportunities/{id}/review/`, depuis Swagger) ; un administrateur peut aussi le
faire depuis l'administration (§5.4).

---

## 5. Guide de l'administrateur

Ouvrez http://localhost:8000/admin/ et connectez-vous (démo : `demo_admin`).

### 5.1 Tableau de bord

La page d'accueil affiche en direct :

- les membres actifs, les publications, les projets et les événements à venir ;
- en **ocre clignotant**, ce qui demande une action : *signalements à traiter* et *annonces à
  valider* ;
- les courbes des nouveaux membres et des publications sur 14 jours.

Chaque indicateur est cliquable et ouvre la liste correspondante.

### 5.2 Gérer les membres

**Comptes → Utilisateurs** :

- rechercher par nom, e-mail ;
- changer le **rôle** (membre, modérateur, administrateur) ;
- actions groupées **désactiver** / **réactiver** des comptes.

Chaque changement de rôle ou d'état est inscrit au journal d'audit.

### 5.3 Traiter les signalements

**Modération → Signalements** : filtres par statut, motif et type de cible. Les actions
groupées permettent de **rejeter** des signalements ou de **masquer** les contenus signalés.
Les décisions détaillées se prennent de préférence depuis la page **Modération** du site.

### 5.4 Valider les opportunités et vérifier les organisations

- **Opportunités → Opportunités** : filtrez sur *En attente de validation*, sélectionnez les
  annonces, puis l'action **Publier** ou **Refuser**. L'auteur est notifié et la décision est
  journalisée.
- **Opportunités → Organisations** : action **Vérifier les organisations sélectionnées**.
  Leurs annonces portent alors le badge « Partenaire vérifié ».

### 5.5 Créer des événements, des communautés, des mentors

Depuis les sections **Événements**, **Communautés** et **Mentorat**, bouton **Ajouter**.

### 5.6 Consulter le journal d'audit

**Modération → Journal d'audit** : toutes les actions sensibles (modération, rôles, comptes,
validations), avec l'auteur, la cible et la date. Il est en **lecture seule**.

### 5.7 Référentiels

**Catalogue** : catégories, technologies, tags et pays proposés dans les formulaires.

---

## 6. Guide du développeur

### 6.1 Organisation du dépôt

| Dossier | Contenu |
|---|---|
| `backend/` | API Django : `config/` (réglages, routes), `common/` (outils partagés, thème de l'administration), `apps/` (un module par domaine), `tests/` |
| `frontend/` | Site Next.js : `src/app/` (pages), `src/components/` (interface et animations), `src/lib/` (client API, authentification) |
| `docs/` | Cahier des charges, guides, décisions d'architecture |
| `docker/` | Image de l'API |
| `requirements/` | Dépendances Python figées |

### 6.2 Développer sans Docker pour l'API

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows ; sous macOS/Linux : source .venv/bin/activate
pip install -r requirements/dev.txt
docker compose up -d db
python backend/manage.py migrate
python backend/manage.py seed_demo
python backend/manage.py runserver
```

Pour le site, dans un second terminal :

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

### 6.3 Vérifier la qualité

| Vérification | Commande |
|---|---|
| Tests backend et couverture | `python -m pytest --cov` |
| Style Python | `ruff check .` puis `ruff format --check .` |
| Contrôle de production | `python backend/manage.py check --deploy` (réglages `prod`) |
| Lint du site | `npm run lint` (dans `frontend/`) |
| Types | `npm run typecheck` |
| Tests du site | `npm test` |
| Build de production | `npm run build` |

Ces vérifications sont aussi lancées automatiquement par GitHub Actions à chaque envoi.

### 6.4 Utiliser l'API

- Documentation interactive : http://localhost:8000/api/docs/ (bouton **Authorize** avec un
  jeton obtenu via `POST /api/v1/auth/login/`).
- Guide d'intégration : `docs/api.md` (authentification, pagination, erreurs, parcours).

### 6.5 Commandes d'exploitation

| Commande | Effet |
|---|---|
| `python backend/manage.py seed_demo` | Données de démonstration (sans doublons si relancée) |
| `python backend/manage.py seed_reference` | Référentiels seuls (utilisable en production) |
| `python backend/manage.py rebuild_search_index` | Reconstruit l'index de recherche |
| `python backend/manage.py recompute_reputation` | Recalcule réputations et badges |
| `python backend/manage.py send_event_reminders` | Envoie les rappels d'événements (à planifier) |

Avec Docker, préfixez par `docker compose exec backend` et remplacez `backend/manage.py` par
`manage.py`.

### 6.6 Variables d'environnement principales

| Variable | Rôle |
|---|---|
| `DJANGO_SECRET_KEY` | Clé secrète (obligatoire en production) |
| `DJANGO_ALLOWED_HOSTS` | Noms de domaine autorisés pour l'API |
| `DATABASE_URL` | Connexion PostgreSQL |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | Adresse(s) du site |
| `FRONTEND_URL` | Adresse du site utilisée dans les e-mails et l'administration |
| `NEXT_PUBLIC_API_BASE_URL` | Adresse de l'API vue par le navigateur (figée à la construction du site) |

La liste complète est dans `.env.example`.

---

## 7. Dépannage

| Problème | Solution |
|---|---|
| Le site affiche une erreur de connexion à l'API | Vérifiez que Docker Desktop tourne, puis `docker compose ps` : les trois services doivent être *running*. Relancez avec `docker compose up -d`. |
| Port déjà utilisé | Changez `FRONTEND_PORT`, `BACKEND_PORT` ou `POSTGRES_HOST_PORT` dans `.env`. |
| Je ne reçois pas l'e-mail de réinitialisation | En local, les e-mails sont écrits dans les journaux : `docker compose logs backend`, puis cherchez le lien `http://localhost:3000/reinitialiser-mot-de-passe?...`. |
| « Ce lien est invalide ou a expiré » | Les liens sont à usage unique et limités dans le temps : demandez-en un nouveau. |
| Je suis déconnecté après un moment | Normal après plusieurs jours d'inactivité : reconnectez-vous. |
| Trop de tentatives de connexion | Une limite protège contre les attaques : patientez une minute. |
| Les données de démo n'apparaissent pas | Relancez `docker compose exec backend python manage.py seed_demo`. |
| Les animations me gênent | Activez « réduire les animations » dans les réglages d'accessibilité de votre système : le site et l'administration les désactivent. |

---

## 8. Limites connues

- Les e-mails ne partent réellement qu'avec un serveur SMTP configuré.
- Pas de temps réel : messages et notifications se rafraîchissent à intervalle régulier.
- Certaines fonctions avancées n'ont pas encore d'écran (marquées 🟡 au §2) : elles sont
  utilisables depuis l'administration ou l'API.
- Pièces jointes de projet et interface anglaise non livrées.
- La plateforme n'est pas déployée publiquement : elle se lance en local.

*Toutes les données de démonstration sont fictives.*
