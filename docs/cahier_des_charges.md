# CAHIER DES CHARGES FONCTIONNEL ET TECHNIQUE

## Plateforme communautaire et collaborative pour les développeurs africains

**Projet :** espace numérique d'échange, d'entraide et de collaboration de la communauté tech africaine  
**Concours :** CADEV 2026  
**Thème communiqué :** « Concevoir l’espace où la communauté tech africaine échangera demain »  
**Nom de travail :** AfriDev Community (nom provisoire, à valider)  
**Version du document :** 1.0  
**Date :** 13 novembre 2026  
**Statut :** spécification de référence avant développement

> **Important :** ce document constitue une proposition de conception détaillée construite à partir du thème communiqué et des orientations du projet. Il ne prétend pas reproduire un règlement officiel ou des critères de notation qui n'ont pas été fournis. Les exigences officielles du concours, la durée exacte, les livrables imposés et les critères du jury devront être vérifiés auprès de l'organisateur avant le gel du périmètre.

---

# 0. Décisions structurantes

Cette section fixe les décisions à respecter pendant le développement. Elle évite que chaque membre de l'équipe interprète le produit différemment.

## 0.1. Nature du produit

AfriDev Community est une **plateforme communautaire de discussion destinée aux développeurs africains**. Elle permet à ses membres de partager des connaissances, de poser des questions techniques, de présenter leurs réalisations, de rencontrer d'autres développeurs et de transformer certains échanges en collaborations concrètes.

Le produit ne doit pas être conçu comme une simple copie de Stack Overflow, Discord, GitHub ou LinkedIn. Il doit articuler trois dimensions dans un parcours cohérent :

1. **Échanger :** poser des questions, partager une expérience, publier une ressource et discuter d'un sujet technique.
2. **Se connecter :** découvrir des développeurs, identifier des compétences complémentaires et proposer une collaboration.
3. **Construire :** former une équipe, organiser un projet, suivre les tâches et présenter les réalisations.

La promesse centrale est la suivante :

> **Aider les développeurs africains à trouver des réponses, des pairs et des collaborateurs pour passer de la discussion à la réalisation de projets concrets.**

Le parcours produit recherché est :

`DISCUSSION → RENCONTRE → ÉQUIPE → PROJET → RÉALISATION → OPPORTUNITÉ`

Ce parcours constitue une orientation de conception, pas une obligation pour chaque utilisateur. Un membre doit pouvoir utiliser la plateforme uniquement pour lire ou participer aux discussions.

## 0.2. Priorité au thème du concours

Le noyau du produit reste l'échange communautaire. Les fonctionnalités de projet, de recherche de coéquipiers, de mentorat et d'opportunités sont des extensions destinées à enrichir cet échange.

En conséquence :

- une discussion doit être utile même lorsqu'elle ne débouche sur aucun projet ;
- la plateforme doit être utilisable dès qu'une personne crée un compte et rejoint la communauté ;
- la collaboration ne doit pas empêcher la livraison d'un espace de discussion stable ;
- les modules secondaires ne doivent jamais retarder les fonctions fondamentales de publication, de consultation, de réponse et de modération.

## 0.3. Décision technologique : React, Vue.js et Next.js

La demande initiale mentionne React, Vue.js et Next.js. Ces trois technologies ne correspondent pas à trois couches complémentaires : **React et Vue.js sont deux frameworks/bibliothèques d'interface distincts**, tandis que **Next.js est un framework construit autour de React**. Utiliser simultanément React et Vue.js pour le même frontend ajouterait une architecture inutilement complexe, des conventions différentes et davantage de travail de maintenance.

**Stack retenue :**

- **Backend :** Python + Django + Django REST Framework.
- **Frontend :** React + Next.js (App Router) + TypeScript.
- **Base de données :** PostgreSQL.
- **Style et composants :** Tailwind CSS, avec une bibliothèque de composants cohérente si nécessaire.
- **Contrat API :** API REST versionnée et documentée avec OpenAPI.

**Vue.js n'est pas retenu dans la version du projet décrite ici.** Il ne sera pas ajouté uniquement pour satisfaire une liste de technologies. Une architecture multi-frontend React/Vue n'aurait de sens que pour des besoins indépendants, une équipe dédiée et un périmètre qui le justifie, ce qui n'est pas le cas d'un hackathon.

Next.js est présenté dans sa documentation officielle comme un framework React fournissant notamment des mécanismes de routage, de récupération des données et de rendu : [documentation React et Next.js](https://nextjs.org/learn/react-foundations/what-is-react-and-nextjs).

## 0.4. Principes non négociables

- Interface **mobile-first** : la plateforme doit être confortable sur téléphone, tablette et ordinateur.
- Langue initiale : français. L'architecture doit permettre l'ajout de l'anglais sans réécriture majeure.
- La plateforme doit rester utilisable avec une connexion moyenne ou instable.
- Les informations importantes doivent être recherchables et paginées.
- Les actions sensibles doivent être contrôlées côté serveur, jamais uniquement dans le navigateur.
- Les compétences déclarées ne doivent pas être présentées comme des compétences vérifiées.
- Les annonces d'opportunités et les comptes doivent pouvoir être signalés et modérés.
- Les fonctionnalités non terminées ne doivent pas être présentées comme opérationnelles pendant la démonstration.
- Le backend Django est la source de vérité des règles métier et des données.

---

# 1. Présentation générale du projet

## 1.1. Contexte

Les développeurs échangent déjà sur plusieurs espaces : plateformes de questions/réponses, réseaux sociaux professionnels, serveurs de discussion, dépôts de code, blogs techniques et communautés spécialisées. Ces outils répondent à des besoins réels, mais les échanges, les profils, les collaborations et les réalisations sont souvent dispersés.

Le projet propose un espace communautaire orienté vers les développeurs africains, avec un démarrage francophone. Il ne cherche pas à remplacer tous les outils existants. Il cherche à rendre plus fluide le passage entre une question technique, la découverte de personnes compétentes, la constitution d'une équipe et la valorisation d'un projet.

## 1.2. Problématique

Un développeur peut avoir besoin de :

- trouver une réponse technique adaptée à son contexte ;
- partager une difficulté sans devoir rejoindre plusieurs communautés ;
- découvrir des développeurs qui utilisent les mêmes technologies ;
- trouver un coéquipier pour une idée de projet ;
- présenter ses réalisations au-delà d'une simple liste de compétences ;
- trouver un mentor, un stage, un emploi, un hackathon ou une opportunité pertinente ;
- retrouver plus tard une solution ou une discussion utile.

Le projet doit répondre à ces besoins sans devenir un assemblage désordonné de fonctionnalités.

## 1.3. Objectif général

Concevoir et mettre en œuvre une plateforme web communautaire permettant aux développeurs africains de discuter, partager leurs connaissances, construire leur réseau technique et initier des collaborations autour de projets concrets.

## 1.4. Objectifs spécifiques

1. Permettre la création d'un profil développeur structuré.
2. Faciliter la publication et la consultation de discussions techniques.
3. Organiser les échanges par catégories, technologies et sujets.
4. Permettre aux membres de poser des questions et de publier des réponses.
5. Faciliter la recherche de développeurs selon leurs compétences, technologies, pays et disponibilités.
6. Permettre la publication d'appels à collaboration.
7. Permettre la création d'espaces de projets et la gestion d'un travail collectif simple.
8. Valoriser les réalisations et contributions vérifiables des membres.
9. Proposer, à terme, des espaces pour les opportunités, le mentorat, les événements et les communautés spécialisées.
10. Fournir aux administrateurs des outils de modération et de gestion de la communauté.

## 1.5. Résultats attendus

À la fin du développement du MVP, un utilisateur doit pouvoir :

- créer un compte et compléter son profil ;
- consulter les publications de la communauté ;
- publier une discussion ou une question ;
- répondre à une question et consulter les réponses ;
- rechercher des contenus par mot-clé, catégorie ou technologie ;
- découvrir un autre développeur et consulter son profil public ;
- publier un projet ouvert à la collaboration ;
- demander à rejoindre une équipe ;
- consulter un espace projet et participer à son suivi ;
- signaler un contenu inapproprié ;
- recevoir une notification liée à une action importante ;
- présenter les résultats du projet à travers une interface opérationnelle et des données de démonstration cohérentes.

---

# 2. Périmètre et priorisation

## 2.1. Méthode de priorisation

Les fonctionnalités sont classées selon quatre niveaux :

| Priorité | Signification | Règle de décision |
|---|---|---|
| **P0 – Indispensable** | Nécessaire au MVP et à la démonstration centrale | À livrer avant toute extension |
| **P1 – Importante** | Renforce nettement la proposition de valeur | À livrer si le socle P0 est stable |
| **P2 – Extension** | Apporte une valeur réelle mais n'est pas nécessaire au premier parcours | À développer après le MVP ou si le temps le permet |
| **P3 – Évolution** | Fonction avancée ou coûteuse | À conserver dans la feuille de route, pas dans le sprint initial |

La priorité décrit l'importance fonctionnelle, pas l'ordre précis des tâches techniques. Certaines tâches techniques transversales (authentification, modèle utilisateur, permissions, design system) doivent être faites tôt parce qu'elles conditionnent les autres modules.

## 2.2. Périmètre du MVP hackathon

Le MVP doit prouver une boucle d'usage complète :

`S'inscrire → compléter son profil → consulter ou publier → échanger → découvrir un développeur → rejoindre ou lancer un projet → suivre une première tâche.`

### Fonctions P0

| ID | Fonctionnalité | Description courte |
|---|---|---|
| P0-01 | Inscription et authentification | Création de compte, connexion, déconnexion, récupération de compte si le service mail est disponible |
| P0-02 | Profils développeurs | Informations publiques, pays, technologies, compétences, liens externes et disponibilité |
| P0-03 | Fil communautaire | Consultation des publications récentes et navigation par catégories |
| P0-04 | Publications | Création, modification et suppression logique de discussions et questions |
| P0-05 | Commentaires et réponses | Participation aux discussions et réponses aux questions |
| P0-06 | Votes utiles | Vote positif sur les contenus ou réponses, avec unicité par membre et cible |
| P0-07 | Catégories et technologies | Classification des contenus pour faciliter leur découverte |
| P0-08 | Recherche et filtres | Recherche simple dans les contenus et profils publics |
| P0-09 | Appels à collaboration | Publication d'un besoin de coéquipiers lié à un projet |
| P0-10 | Demandes pour rejoindre | Envoi, acceptation ou refus d'une demande d'intégration à un projet |
| P0-11 | Espace projet simple | Présentation du projet, membres, rôles, lien GitHub, tâches simples et statut |
| P0-12 | Signalement | Signalement d'un contenu ou profil et traitement minimal par un modérateur |
| P0-13 | Administration minimale | Gestion des utilisateurs, catégories, contenus signalés et contenus de démonstration |
| P0-14 | Interface responsive | Utilisation correcte sur mobile et desktop |

### Fonctions P1

- profils enrichis avec projets, contributions et disponibilité détaillée ;
- filtres avancés de découverte de développeurs ;
- articles/tutoriels techniques avec mise en forme ;
- réponses acceptées pour les questions ;
- favoris et contenus enregistrés ;
- abonnements à des membres ou sujets ;
- notifications internes ;
- gestion de tâches plus complète, échéances et jalons ;
- mises à jour d'un projet et fil d'activité ;
- badges et réputation fondés sur des actions réelles ;
- tableau de bord utilisateur ;
- contrôle de profil privé/public et paramètres de notification ;
- interface anglaise préparée ou première traduction selon le temps disponible.

### Fonctions P2

- annuaire d'opportunités : stages, emplois, missions freelance, bourses et hackathons ;
- candidatures ou demandes d'information sur les opportunités ;
- mentorat : profils de mentors, demandes, suivi de sessions ;
- communautés par pays, ville, université, technologie ou domaine ;
- événements communautaires, agenda et inscriptions ;
- messagerie privée entre membres ;
- recommandations de développeurs et de projets à partir des compétences et centres d'intérêt ;
- portfolio enrichi de réalisations ;
- pages d'organisation ou de partenaire vérifié ;
- notifications par e-mail.

### Fonctions P3

- connexion OAuth avec GitHub et synchronisation facultative de dépôts ou contributions ;
- analyse de contributions GitHub plus poussée ;
- assistant IA d'aide à la formulation d'une question, de résumé d'une discussion ou d'orientation vers une ressource ;
- moteur de recommandation personnalisé ;
- messagerie temps réel, appels audio/vidéo ou salons live ;
- application mobile native ;
- PWA avancée avec mise en cache hors ligne ;
- traduction assistée et prise en charge de langues africaines ;
- système de validation de compétences par pairs, tests ou projets évalués ;
- intégrations externes avancées (GitHub, calendrier, outils de gestion de code) ;
- statistiques avancées pour les communautés et partenaires.

## 2.3. Hors périmètre du MVP

Les éléments suivants ne doivent pas être développés avant que les fonctions P0 soient stables :

- hébergement de dépôts Git et remplacement de GitHub ;
- éditeur de code collaboratif intégré ;
- visioconférence intégrée ;
- système de paiement ou de facturation ;
- marketplace complète de freelances ;
- système de recrutement de bout en bout ;
- intelligence artificielle conversationnelle généraliste ;
- application mobile native ;
- microservices, Kubernetes ou architecture distribuée complexe.

Ces éléments peuvent être évoqués dans la vision future, mais ne doivent pas gonfler artificiellement la démonstration du hackathon.

---

# 3. Public cible, utilisateurs et rôles

## 3.1. Public cible initial

**Cible prioritaire :** développeurs, étudiants en informatique, autodidactes, ingénieurs logiciels, administrateurs systèmes/réseaux, spécialistes cybersécurité, data practitioners et autres profils techniques résidant en Afrique ou liés à des communautés tech africaines.

**Approche de lancement proposée :** démarrer avec une communauté francophone, notamment en Afrique de l'Ouest, tout en évitant de verrouiller l'application sur un seul pays. L'anglais doit pouvoir être ajouté facilement.

Cette stratégie de lancement est une hypothèse de produit à valider, pas une limitation définitive de la plateforme.

## 3.2. Personae de référence

### Persona A – L'apprenant

- Étudiant ou débutant en programmation.
- Cherche des explications, des retours et des personnes pouvant l'aider.
- A besoin d'une interface compréhensible, de catégories claires et d'un profil simple.

### Persona B – Le développeur actif

- Réalise des projets personnels ou professionnels.
- Souhaite résoudre des problèmes précis, partager des ressources et trouver des collaborateurs.
- A besoin de discussions bien organisées, de recherche et de profils techniques crédibles.

### Persona C – Le porteur de projet

- A une idée ou un projet en cours.
- Cherche des profils complémentaires (frontend, backend, design, réseau, sécurité, data, etc.).
- A besoin de publier un appel à collaboration, de recevoir des demandes et de suivre le travail.

### Persona D – Le mentor ou expert

- Possède une expérience dans un domaine technique.
- Souhaite contribuer à la communauté et éventuellement accompagner des membres.
- A besoin d'une bonne visibilité de ses domaines d'expertise et d'outils de discussion.

### Persona E – Le modérateur

- Veille à la qualité et à la sécurité des échanges.
- Traite les signalements, masque les contenus problématiques et applique les règles de la communauté.

## 3.3. Rôles applicatifs

Les rôles globaux sont indépendants des rôles attribués dans un projet.

| Rôle | Description | Principales permissions |
|---|---|---|
| Visiteur | Utilisateur non connecté | Consulter les contenus publics et profils publics, rechercher, créer un compte |
| Membre | Utilisateur connecté | Publier, commenter, répondre, voter, enregistrer, signaler, créer un projet et demander à rejoindre une équipe |
| Modérateur | Membre habilité à modérer | Consulter la file de signalements, masquer/restaurer du contenu, suspendre temporairement selon les règles |
| Administrateur | Responsable de la plateforme | Gérer les comptes, rôles, catégories, référentiels, signalements, paramètres et journaux d'administration |
| Partenaire vérifié | Organisation autorisée, évolution P2 | Publier des opportunités après validation et gérer ses annonces |

Un membre peut également avoir un rôle **dans un projet** : propriétaire, responsable, contributeur ou observateur. Ce rôle local ne lui donne aucun privilège global sur la plateforme.

## 3.4. Matrice simplifiée des permissions

| Action | Visiteur | Membre | Modérateur | Administrateur |
|---|---:|---:|---:|---:|
| Lire un contenu public | Oui | Oui | Oui | Oui |
| Rechercher des contenus publics | Oui | Oui | Oui | Oui |
| Créer une publication | Non | Oui | Oui | Oui |
| Commenter/répondre/voter | Non | Oui | Oui | Oui |
| Modifier son propre contenu | Non | Oui | Oui | Oui |
| Modifier le contenu d'un autre membre | Non | Non | Selon modération | Oui |
| Signaler un contenu | Non | Oui | Oui | Oui |
| Traiter un signalement | Non | Non | Oui | Oui |
| Gérer les rôles globaux | Non | Non | Non | Oui |
| Créer un projet | Non | Oui | Oui | Oui |
| Gérer son projet | Non | Selon rôle projet | Selon rôle projet | Oui |

Les restrictions doivent être appliquées dans Django REST Framework, pas uniquement en masquant des boutons dans React.

---

# 4. Spécifications fonctionnelles détaillées

Chaque exigence porte un identifiant pour pouvoir être reliée au code, aux tests et à la recette.

## 4.1. Module A – Inscription, connexion et compte utilisateur

**Priorité : P0**

### A.1. Fonctionnalités

- Inscription par adresse e-mail, nom d'utilisateur et mot de passe.
- Connexion par e-mail ou nom d'utilisateur selon la décision de conception retenue.
- Déconnexion.
- Vérification de l'adresse e-mail si un service d'envoi est configuré.
- Réinitialisation du mot de passe via un lien à durée limitée si l'e-mail est opérationnel.
- Consultation et modification des informations de compte.
- Fermeture ou désactivation du compte selon la politique de conservation.
- Protection contre les tentatives répétées de connexion.

### A.2. Règles métier

- L'adresse e-mail doit être unique et normalisée.
- Le nom d'utilisateur doit être unique, sans espaces et limité à un format documenté.
- Le mot de passe doit respecter une politique minimale de robustesse.
- Les mots de passe sont hachés par Django ; ils ne sont jamais stockés en clair.
- Un compte désactivé ne peut pas effectuer d'action nécessitant une authentification.
- Un utilisateur ne peut modifier ni son rôle global ni son statut de vérification depuis son profil.
- Les changements d'e-mail doivent être confirmés avant de remplacer l'adresse validée.

### A.3. Critères d'acceptation

- Un visiteur peut créer un compte avec des informations valides.
- Un doublon d'e-mail ou de nom d'utilisateur est refusé avec un message compréhensible.
- Un utilisateur incorrectement authentifié ne peut pas accéder aux routes privées.
- Un utilisateur connecté peut se déconnecter et ne plus accéder aux actions protégées.
- Une requête directe à l'API ne permet pas de modifier le rôle d'un utilisateur ordinaire.

## 4.2. Module B – Profil développeur

**Priorité : P0 pour le profil de base, P1 pour le profil enrichi**

### B.1. Informations du profil

| Champ | Obligatoire | Visibilité par défaut | Remarque |
|---|---|---|---|
| Nom d'affichage | Oui | Public | Peut être différent du nom légal |
| Nom d'utilisateur | Oui | Public | Identifiant unique |
| Photo/avatar | Non | Public | Image facultative, taille limitée |
| Biographie | Non | Public | Texte court |
| Pays | Non au départ | Public si renseigné | Liste normalisée |
| Ville | Non | Public si renseignée | Ne pas demander d'adresse privée |
| Langues | Non | Public | Ex. français, anglais |
| Niveau déclaré | Non | Public | Débutant, intermédiaire, avancé, expert, auto-évalué |
| Technologies | Non | Public | Liées au référentiel des technologies |
| Domaines | Non | Public | Web, mobile, réseau, cybersécurité, data, IA, etc. |
| Disponibilité | Non | Public ou privée selon réglage | Ex. ouvert à la collaboration |
| Liens externes | Non | Public | GitHub, LinkedIn, portfolio, site personnel |
| Projets | Non | Public | Projets associés au compte |
| Contributions | Calculé | Public | Discussions, réponses, projets terminés |

### B.2. Fonctionnalités

- Créer et modifier son profil.
- Ajouter ou retirer des technologies et domaines.
- Associer un niveau auto-déclaré à une technologie.
- Ajouter des liens externes avec type et URL.
- Définir sa disponibilité : non disponible, ouvert aux collaborations, recherche un projet, disponible pour du mentorat.
- Définir la visibilité de certains champs.
- Consulter les profils publics des membres.

### B.3. Règles métier

- Les compétences auto-déclarées doivent être distinguées des compétences validées par une preuve.
- La plateforme ne doit pas afficher de badge « vérifié » simplement parce qu'un lien GitHub a été ajouté.
- Une preuve peut être un projet, un dépôt externe, une contribution documentée ou une validation ultérieure par des pairs.
- Une URL externe doit être validée et limitée aux schémas HTTP/HTTPS.
- Les informations privées ne doivent pas être retournées dans les réponses API publiques.

### B.4. Critères d'acceptation

- Un membre peut créer un profil même sans photo ni lien externe.
- Le profil public affiche uniquement les champs publics.
- Un membre peut filtrer l'annuaire par technologie et pays si ces données sont renseignées.
- Une compétence déclarée est visuellement identifiée comme telle.

## 4.3. Module C – Fil communautaire et publications

**Priorité : P0**

Ce module est le cœur du produit et doit être livré avant les extensions.

### C.1. Types de publications

| Type | Usage | Champs spécifiques |
|---|---|---|
| Discussion | Partager une idée ou ouvrir un échange | Titre, contenu, catégorie, tags |
| Question | Demander une aide technique précise | Titre, description du problème, environnement/contexte facultatif |
| Article / tutoriel | Expliquer une méthode ou partager un guide | Titre, contenu structuré, tags |
| Annonce communautaire | Communiquer une information pertinente | Titre, contenu, catégorie |
| Mise à jour de projet | Informer sur l'avancement d'un projet | Projet associé, contenu, statut |

Pour le MVP, Discussion et Question sont obligatoires. Article/tutoriel et annonce peuvent être activés si le temps le permet sans retarder le cœur.

### C.2. Fonctionnalités

- Consulter le fil des publications publiques.
- Trier par date récente et popularité simple.
- Filtrer par type, catégorie et technologie.
- Ouvrir une publication et consulter ses réponses/commentaires.
- Créer une publication.
- Modifier ou supprimer logiquement sa propre publication.
- Ajouter des tags.
- Réagir positivement à une publication.
- Enregistrer une publication en favori (P1).
- Partager le lien public d'une publication.
- Signaler une publication.

### C.3. Règles métier

- Une publication publiée doit avoir un titre et un contenu.
- Le titre doit respecter une longueur maximale documentée.
- Le contenu peut accepter du texte simple et une mise en forme limitée. Le HTML arbitraire ne doit pas être rendu sans assainissement.
- Un contenu supprimé par son auteur est masqué logiquement afin de préserver les références de discussion et la traçabilité.
- Un membre ne peut voter qu'une fois sur une même publication ; il peut retirer son vote.
- Les résultats du fil sont paginés côté serveur.
- Les contenus masqués par modération ne sont pas visibles publiquement.
- Les liens externes doivent être affichés de manière sûre.

### C.4. Fil communautaire

Le fil par défaut présente les publications récentes. Les options de tri P1 peuvent inclure :

- Récent : ordre chronologique décroissant.
- Actif : publications ayant reçu une activité récente.
- Populaire : score de réactions sur une période déterminée.
- Sans réponse : questions ne disposant pas encore de réponse.

Le classement doit rester explicable. Le MVP ne nécessite pas de moteur algorithmique opaque.

### C.5. Critères d'acceptation

- Un membre peut publier une discussion et la retrouver dans le fil.
- Un visiteur peut consulter une publication publique.
- Un membre peut commenter ou voter lorsqu'il est connecté.
- Les filtres renvoient des résultats cohérents.
- Les contenus masqués ne réapparaissent pas dans le fil public.

## 4.4. Module D – Questions, réponses et entraide technique

**Priorité : P0**

### D.1. Fonctionnalités

- Créer une question avec un titre explicite et une description.
- Ajouter des technologies, tags et catégorie.
- Publier une réponse à une question.
- Modifier ou supprimer logiquement sa propre réponse.
- Voter positivement pour une réponse utile.
- Marquer une réponse comme acceptée par l'auteur de la question (P1, mais fortement recommandée).
- Trier les réponses par pertinence ou date.
- Signaler une question ou une réponse.

### D.2. Règles métier

- Une question doit être distincte d'une discussion générale par son type.
- Seul l'auteur de la question peut accepter une réponse.
- Une seule réponse peut être acceptée à la fois.
- L'auteur d'une réponse ne peut pas accepter sa propre réponse, sauf décision explicite contraire de l'équipe ; recommandation : l'interdire.
- Un vote ne doit pas être multiplié en répétant des requêtes.
- La suppression d'une réponse ne doit pas casser l'affichage des autres réponses.

### D.3. Critères d'acceptation

- Un membre peut publier une question et recevoir des réponses.
- L'auteur de la question peut identifier la réponse qui résout son problème.
- Un utilisateur non connecté ne peut ni répondre ni voter.
- Les compteurs de votes sont cohérents avec les votes réellement enregistrés.

## 4.5. Module E – Catégories, technologies et tags

**Priorité : P0**

### E.1. Référentiels initiaux

Les catégories doivent rester administrables. Exemples de catégories initiales :

- Développement web ;
- Développement mobile ;
- Backend et API ;
- Frontend et UI/UX ;
- Réseaux et télécommunications ;
- Cybersécurité ;
- Cloud et DevOps ;
- Data et intelligence artificielle ;
- Bases de données ;
- Systèmes et logiciels libres ;
- Carrière, formation et orientation ;
- Projets et hackathons.

Les technologies peuvent inclure, sans s'y limiter : Python, Django, JavaScript, TypeScript, React, Next.js, Vue.js, Java, PHP, Laravel, Node.js, PostgreSQL, MySQL, Docker, Linux, Cisco, Wireshark, etc.

### E.2. Règles métier

- Une catégorie peut contenir plusieurs publications.
- Une publication peut être associée à plusieurs tags/technologies.
- Les technologies doivent être normalisées pour éviter les doublons de casse ou d'orthographe.
- Seuls les administrateurs peuvent créer, modifier, fusionner ou désactiver un élément de référentiel dans le MVP.
- La désactivation d'un tag ne doit pas supprimer l'historique des publications.

## 4.6. Module F – Recherche et découverte

**Priorité : P0 pour la recherche simple, P1 pour les filtres avancés**

### F.1. Recherche de contenu

La recherche doit permettre de trouver des publications par :

- mots présents dans le titre ;
- mots présents dans le contenu ;
- catégorie ;
- type de publication ;
- technologie ou tag ;
- auteur, lorsque le profil est public.

### F.2. Découverte de développeurs

Filtres souhaités :

- technologie ;
- domaine ;
- pays ;
- ville si renseignée ;
- disponibilité ;
- niveau déclaré ;
- langue.

### F.3. Règles métier

- Les résultats sont paginés.
- Les champs privés ne sont jamais utilisés pour exposer une information cachée.
- Les requêtes doivent être limitées et protégées contre les abus.
- Le classement doit favoriser la pertinence et la fraîcheur sans transformer la découverte en compétition de popularité.

### F.4. Version hackathon

La recherche du MVP peut utiliser les capacités de recherche PostgreSQL et des filtres Django REST Framework. Il n'est pas nécessaire d'intégrer Elasticsearch ou un moteur externe pour un premier concours.

## 4.7. Module G – Appels à collaboration et recherche de coéquipiers

**Priorité : P0**

Ce module matérialise l'une des principales extensions différenciantes du projet : transformer une discussion ou une idée en équipe.

### G.1. Fonctionnalités

- Créer un projet ou un appel à collaboration.
- Décrire le problème, l'idée, les objectifs et le résultat recherché.
- Définir les technologies utilisées ou envisagées.
- Définir les rôles recherchés (frontend, backend, mobile, UI/UX, réseau, cybersécurité, data, rédaction, etc.).
- Préciser le niveau ou les compétences attendues.
- Préciser la disponibilité attendue et le mode de collaboration (à distance, hybride, présentiel).
- Définir le statut : idée, recherche d'équipe, en cours, suspendu, terminé, archivé.
- Consulter les projets ouverts.
- Envoyer une demande pour rejoindre un projet.
- Accepter ou refuser une demande.
- Retirer une demande envoyée.

### G.2. Règles métier

- Le créateur devient propriétaire du projet.
- Un projet peut avoir plusieurs membres et plusieurs rôles recherchés.
- Le créateur peut fermer les candidatures.
- Un membre ne peut pas envoyer plusieurs demandes actives au même projet.
- Une demande acceptée entraîne la création d'une relation de membre de projet.
- Une demande refusée conserve son état pour éviter les doublons abusifs ; le créateur peut autoriser une nouvelle demande après un délai ou une réouverture.
- Les membres ne peuvent pas consulter les demandes privées d'autres candidats.
- Un propriétaire ne peut pas supprimer arbitrairement les contributions personnelles d'un autre membre.
- Le statut et les règles d'accès d'un projet sont vérifiés côté serveur.

### G.3. Critères d'acceptation

- Un membre peut publier un projet ouvert aux collaborateurs.
- Un autre membre peut envoyer une demande motivée pour rejoindre le projet.
- Le propriétaire peut accepter ou refuser cette demande.
- Après acceptation, le nouveau membre apparaît dans la liste des membres avec un rôle défini.
- Un utilisateur non autorisé ne peut pas modifier le projet ou les demandes.

## 4.8. Module H – Espaces de projets

**Priorité : P0 pour les fonctions simples, P1 pour le suivi avancé**

### H.1. Informations d'un projet

- nom ;
- description ;
- problématique ou besoin visé ;
- objectifs ;
- image ou logo facultatif ;
- technologies ;
- catégorie/domaine ;
- date de création ;
- statut ;
- propriétaire ;
- membres et rôles ;
- lien de dépôt GitHub/GitLab ou autre dépôt externe ;
- lien de démonstration ;
- visibilité : public ou privé (P1 si les permissions privées peuvent être correctement testées).

### H.2. Fonctionnalités P0

- consulter la page publique d'un projet ;
- modifier les informations d'un projet selon ses permissions ;
- visualiser les membres et leurs rôles ;
- ajouter un lien de dépôt externe ;
- créer une tâche simple ;
- attribuer une tâche à un membre du projet ;
- changer le statut d'une tâche ;
- consulter les tâches du projet.

### H.3. Fonctionnalités P1

- jalons (milestones) ;
- dates limites ;
- commentaires sur les tâches ;
- fil d'activité ;
- mises à jour de projet ;
- pièces jointes ;
- historique des changements ;
- tableau Kanban simple ;
- invitations directes ;
- gestion avancée des rôles.

### H.4. Rôles dans un projet

| Rôle projet | Permissions |
|---|---|
| Propriétaire | Modifier les paramètres du projet, gérer les membres, accepter les demandes, gérer toutes les tâches |
| Responsable | Gérer les tâches et les membres si le propriétaire lui accorde ce droit |
| Contributeur | Voir l'espace, participer, créer/mettre à jour les tâches autorisées |
| Observateur | Consulter les informations accessibles sans modifier les données |

### H.5. Statuts d'une tâche

- À faire ;
- En cours ;
- En revue ;
- Terminée ;
- Bloquée.

### H.6. Règles métier

- Une tâche appartient à un seul projet.
- Un membre assigné à une tâche doit être membre du projet.
- Une tâche ne peut être marquée comme terminée que par un membre autorisé.
- Le propriétaire peut réaffecter une tâche.
- Une tâche terminée conserve son historique.
- Les échéances sont facultatives dans le MVP.
- Un projet terminé reste consultable selon sa visibilité.

## 4.9. Module I – Réalisations, contributions et réputation

**Priorité : P1**

### I.1. Objectif

Valoriser la participation réelle plutôt que le volume de publications. La réputation ne doit pas être un simple compteur de likes facilement manipulable.

### I.2. Sources de contribution

- réponse acceptée ;
- réponse ayant reçu des votes positifs ;
- contribution à un projet ;
- projet terminé et présenté ;
- tutoriel publié ;
- participation à une communauté ;
- mentorat terminé ;
- recommandation contextualisée par un autre membre.

### I.3. Fonctionnalités

- afficher les projets réalisés ;
- afficher les contributions principales ;
- attribuer des badges définis par des règles explicites ;
- afficher un score de réputation avec une explication de son calcul ;
- permettre de masquer certains éléments du profil.

### I.4. Règles métier

- Les points ne doivent pas être accordés uniquement à la création d'un compte.
- Les actions répétitives ou automatisées doivent être limitées.
- Un membre ne peut pas se donner une recommandation.
- Les badges doivent être liés à des seuils vérifiables.
- L'équipe doit documenter le calcul de réputation avant de l'afficher.
- Le score de réputation ne doit pas être utilisé comme preuve absolue de compétence.

## 4.10. Module J – Notifications

**Priorité : P1 pour les notifications internes simples**

### J.1. Événements notifiables

- réponse à une question ;
- commentaire sur une publication ;
- vote ou réaction significative ;
- demande reçue pour rejoindre un projet ;
- demande acceptée ou refusée ;
- nouvelle tâche assignée ;
- modification importante d'un projet ;
- message privé reçu (P2) ;
- rappel d'événement (P2).

### J.2. Fonctionnalités

- liste des notifications ;
- état lu/non lu ;
- marquer une notification comme lue ;
- marquer toutes les notifications comme lues ;
- redirection vers l'élément concerné.

### J.3. Règles métier

- Une notification est personnelle.
- Un utilisateur ne doit pas recevoir de notification pour une action qu'il a lui-même effectuée, sauf cas justifié.
- Les notifications sont paginées.
- Les informations sensibles ne doivent pas être exposées dans le texte de notification.

## 4.11. Module K – Favoris, abonnements et personnalisation

**Priorité : P1**

Fonctionnalités envisagées :

- enregistrer une publication ;
- consulter ses publications sauvegardées ;
- suivre un membre ;
- suivre une technologie ou catégorie ;
- consulter un fil personnalisé ;
- gérer les abonnements.

Règle : le fil personnalisé ne doit jamais remplacer le fil communautaire général. L'utilisateur doit pouvoir revenir aux contenus récents de toute la communauté.

## 4.12. Module L – Opportunités

**Priorité : P2**

### L.1. Types d'opportunités

- emploi ;
- stage ;
- mission freelance ;
- bourse ;
- hackathon ;
- programme d'incubation ;
- formation ou certification ;
- appel à projets.

### L.2. Informations d'une opportunité

- titre ;
- organisation ;
- type ;
- description ;
- pays/zone géographique ;
- modalité (présentiel, hybride, distant) ;
- niveau requis ;
- compétences recherchées ;
- date limite ;
- lien officiel de candidature ;
- contact éventuel ;
- statut (brouillon, en attente de validation, publié, expiré, suspendu).

### L.3. Règles métier

- Toute annonce doit avoir une source ou un moyen de vérification.
- Les annonces suspectes peuvent être signalées.
- Les offres expirées doivent être clairement identifiées.
- Les utilisateurs ne doivent jamais être obligés de payer pour accéder à une annonce publiée gratuitement sur la plateforme.
- Les publications par un partenaire doivent être soumises à une vérification de son identité ou de son organisation.
- Le MVP ne traite pas les paiements ni le recrutement complet.

## 4.13. Module M – Mentorat

**Priorité : P2**

### Fonctionnalités

- déclarer une disponibilité pour le mentorat ;
- présenter les domaines d'expertise ;
- rechercher un mentor par domaine et langue ;
- envoyer une demande de mentorat avec un objectif ;
- accepter ou refuser une demande ;
- définir une session ou un rendez-vous ;
- marquer une session comme terminée ;
- laisser un retour après la session.

### Règles

- Le mentorat doit être volontaire et explicite.
- Une demande n'est pas automatiquement acceptée.
- Les coordonnées personnelles ne sont pas publiques par défaut.
- Les sessions et les retours doivent respecter les règles de confidentialité.

## 4.14. Module N – Communautés thématiques et géographiques

**Priorité : P2**

### Exemples

- Communautés par pays ;
- communautés par ville ;
- communautés universitaires ;
- communautés par technologie ;
- communautés par domaine : cybersécurité, réseaux, développement mobile, IA, cloud, etc.

### Fonctionnalités

- créer une communauté ;
- définir un nom, une description, une catégorie et des règles ;
- rejoindre ou quitter une communauté ;
- publier dans cette communauté ;
- désigner des responsables ;
- modérer les publications locales.

### Règles

- Une communauté possède au moins un responsable.
- Les règles locales ne peuvent pas contredire les règles générales de la plateforme.
- La communauté ne doit pas devenir un espace de spam ou de promotion sans rapport avec son thème.

## 4.15. Module O – Événements

**Priorité : P2**

### Fonctionnalités

- publier un événement technique ;
- préciser le format, la date, le lieu ou le lien de participation ;
- consulter les événements à venir ;
- s'inscrire ou se désinscrire ;
- recevoir un rappel ;
- afficher les événements passés.

### Exemples

Meetups, ateliers, conférences, webinaires, compétitions, hackathons, sessions de mentorat collectif.

## 4.16. Module P – Messagerie privée

**Priorité : P2**

### Fonctionnalités

- démarrer une conversation entre deux membres ;
- envoyer un message texte ;
- consulter l'historique ;
- signaler ou bloquer un utilisateur ;
- marquer une conversation comme lue.

### Règles

- Un membre bloqué ne peut plus envoyer de message au membre qui l'a bloqué.
- Les messages ne sont visibles que par les participants et les administrateurs habilités selon une procédure de sécurité documentée.
- La messagerie doit être protégée contre le spam et les liens malveillants.
- Le temps réel n'est pas obligatoire au lancement : un rafraîchissement périodique ou une consultation classique suffit au premier stade.

## 4.17. Module Q – Modération, confiance et sécurité communautaire

**Priorité : P0 pour le signalement et la modération minimale, P1/P2 pour les outils avancés**

### Q.1. Contenus concernés

- publications ;
- commentaires ;
- réponses ;
- profils ;
- projets ;
- opportunités ;
- messages privés lorsque le processus de signalement le permet.

### Q.2. Motifs de signalement

- spam ;
- arnaque ou offre trompeuse ;
- harcèlement ou intimidation ;
- contenu haineux ou discriminatoire ;
- usurpation d'identité ;
- contenu dangereux ou illégal ;
- violation de propriété intellectuelle ;
- autre motif avec commentaire.

### Q.3. Workflow de modération

`Signalement créé → En attente → En cours d'examen → Action prise ou rejeté → Clôturé`

Actions possibles :

- aucune action ;
- avertissement ;
- masquage temporaire ;
- suppression logique ;
- suspension temporaire du compte ;
- bannissement selon décision administrative.

### Q.4. Règles métier

- Un utilisateur ne peut pas traiter ses propres signalements.
- Toute action de modération doit être journalisée avec auteur, date, motif et cible.
- Un signalement ne signifie pas automatiquement qu'un contenu est coupable.
- Le membre concerné doit recevoir une information adaptée lorsqu'une action affecte son compte ou son contenu, dans les limites de sécurité.
- Les administrateurs peuvent restaurer un contenu masqué par erreur.

## 4.18. Module R – Administration

**Priorité : P0**

### Fonctionnalités minimales

- consulter les utilisateurs ;
- désactiver ou réactiver un compte ;
- attribuer les rôles globaux autorisés ;
- gérer les catégories et référentiels ;
- consulter les publications ;
- traiter les signalements ;
- gérer les contenus masqués ;
- consulter les statistiques simples ;
- consulter les journaux des actions sensibles.

Django Admin peut être utilisé comme interface initiale d'administration, à condition de configurer correctement les permissions et d'éviter d'exposer cette interface aux membres ordinaires. Une interface de modération dédiée peut être ajoutée au frontend si le temps le permet.

---

# 5. Parcours utilisateurs de référence

Les parcours ci-dessous servent de base aux écrans, endpoints API et tests de bout en bout.

## 5.1. Parcours 1 – Un nouveau membre rejoint la communauté

1. Il arrive sur la page d'accueil.
2. Il consulte une présentation de la plateforme et quelques discussions publiques.
3. Il clique sur « Créer un compte ».
4. Il renseigne e-mail, nom d'utilisateur et mot de passe.
5. Il se connecte.
6. Il complète son profil : pays, domaines, technologies, liens facultatifs.
7. Il accède au fil communautaire.
8. Il peut suivre une catégorie ou rechercher une discussion.

**Résultat attendu :** le membre comprend immédiatement à quoi sert la plateforme et peut participer sans remplir un formulaire interminable.

## 5.2. Parcours 2 – Un membre pose une question technique

1. Il ouvre « Poser une question ».
2. Il rédige un titre précis.
3. Il décrit le problème, le résultat attendu, le résultat obtenu et son environnement.
4. Il sélectionne une catégorie et des technologies.
5. Il publie.
6. Les autres membres consultent la question et proposent des réponses.
7. L'auteur peut voter pour les réponses et, dans la version P1, accepter celle qui résout le problème.

**Résultat attendu :** une question devient un contenu consultable et réutilisable par la communauté.

## 5.3. Parcours 3 – Un développeur recherche un coéquipier

1. Il crée un projet.
2. Il décrit le besoin et les objectifs.
3. Il ajoute les technologies.
4. Il indique les rôles recherchés.
5. Il ouvre le projet aux candidatures.
6. D'autres membres découvrent le projet.
7. Un membre envoie une demande motivée.
8. Le propriétaire consulte les demandes et accepte ou refuse.
9. Si la demande est acceptée, le candidat devient membre du projet.

**Résultat attendu :** le projet dispose d'une équipe initiale et les responsabilités sont identifiables.

## 5.4. Parcours 4 – Une équipe suit un projet

1. Le propriétaire renseigne le projet et son dépôt externe.
2. Il ajoute les tâches initiales.
3. Il assigne les tâches aux membres.
4. Les membres mettent à jour les statuts.
5. L'équipe consulte la progression.
6. Une mise à jour présente les résultats obtenus.
7. Le projet peut être marqué terminé et apparaître dans les réalisations.

## 5.5. Parcours 5 – Un membre signale un contenu

1. Il ouvre le menu d'une publication ou d'un profil.
2. Il choisit « Signaler ».
3. Il sélectionne un motif et ajoute un commentaire facultatif.
4. Le signalement est enregistré.
5. Un modérateur consulte la file de traitement.
6. Il examine le contenu et décide d'une action.
7. L'action est conservée dans l'historique.

---

# 6. Architecture fonctionnelle et technique

## 6.1. Architecture générale

Architecture recommandée : **monolithe modulaire avec frontend séparé**.

```text
┌───────────────────────────────────────────────┐
│                 UTILISATEUR                    │
│       Navigateur mobile / tablette / PC        │
└──────────────────────┬────────────────────────┘
                       │ HTTPS
                       ▼
┌───────────────────────────────────────────────┐
│           FRONTEND : NEXT.JS + REACT            │
│                 TypeScript                     │
│  Pages / composants / formulaires / navigation │
└──────────────────────┬────────────────────────┘
                       │ API REST JSON
                       ▼
┌───────────────────────────────────────────────┐
│              BACKEND : DJANGO                  │
│          Django REST Framework                 │
│ Auth / règles métier / permissions / API       │
│ Profils / communauté / projets / modération    │
└──────────────────────┬────────────────────────┘
                       │ ORM Django
                       ▼
┌───────────────────────────────────────────────┐
│                POSTGRESQL                      │
│ Comptes / profils / publications / projets     │
│ Relations / notifications / historique        │
└───────────────────────────────────────────────┘

Services facultatifs : Redis, Celery, stockage objet, e-mail.
```

### Pourquoi un monolithe modulaire ?

Un monolithe modulaire regroupe les fonctionnalités dans une application backend structurée en modules, sans multiplier les services indépendants. C'est plus simple à développer, tester et déployer dans un hackathon qu'une architecture microservices.

## 6.2. Stack technique retenue

| Couche | Technologie | Rôle |
|---|---|---|
| Langage backend | Python | Logique serveur |
| Framework backend | Django | Modèles, administration, sécurité, logique applicative |
| API | Django REST Framework | Endpoints REST, sérialisation, authentification et permissions |
| Langage frontend | TypeScript | Typage et robustesse du frontend |
| Bibliothèque UI | React | Construction des composants et interfaces |
| Framework frontend | Next.js App Router | Routage, rendu, organisation des pages et optimisation |
| CSS | Tailwind CSS | Mise en forme responsive |
| Base de données | PostgreSQL | Stockage relationnel |
| Documentation API | OpenAPI / Swagger UI | Contrat lisible entre frontend et backend |
| Tests backend | pytest + pytest-django ou unittest Django | Tests unitaires et API |
| Tests frontend | Vitest + Testing Library | Tests de composants et logique UI |
| Tests parcours | Playwright | Tests de bout en bout |
| Conteneurisation | Docker Compose | Environnement reproductible |
| Versionnement | Git + GitHub/GitLab | Collaboration et historique |

### Versions

Au début du développement, l'équipe doit sélectionner les versions stables et compatibles des composants, puis les figer dans les fichiers de dépendances (`requirements.txt` ou `pyproject.toml`, lockfile frontend). Ne pas utiliser des versions flottantes ou `latest` sans contrôle.

La documentation de Django publie les versions prises en charge et les périodes de support : [Django – versions prises en charge](https://www.djangoproject.com/download/). La documentation de Django REST Framework indique les versions de Django et Python compatibles : [Django REST Framework](https://www.django-rest-framework.org/).

## 6.3. Responsabilité des couches

### Frontend Next.js / React

Responsable de :

- affichage des pages ;
- navigation ;
- formulaires et validations ergonomiques ;
- états de chargement, succès et erreur ;
- appels à l'API ;
- affichage conditionnel selon les droits connus ;
- rendu responsive et accessibilité.

Le frontend ne doit pas être la seule protection d'une action. Une personne peut appeler l'API sans passer par l'interface.

### Backend Django / DRF

Responsable de :

- authentification ;
- autorisation ;
- validation des données ;
- règles métier ;
- cohérence transactionnelle ;
- filtres, recherche et pagination ;
- création de notifications ;
- journalisation des actions sensibles ;
- exposition de l'API.

### PostgreSQL

Responsable de la persistance des données, des clés étrangères, contraintes d'unicité, index et transactions.

## 6.4. Organisation recommandée du backend

Structure indicative :

```text
backend/
├── config/
│   ├── settings/
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── accounts/
│   ├── profiles/
│   ├── catalog/
│   ├── community/
│   ├── collaboration/
│   ├── projects/
│   ├── reputation/
│   ├── opportunities/
│   ├── mentorship/
│   ├── communities/
│   ├── events/
│   ├── messaging/
│   ├── notifications/
│   └── moderation/
├── common/
├── tests/
├── manage.py
└── requirements.txt
```

Pour le MVP, certaines apps P2 peuvent ne pas être créées immédiatement. Les noms représentent des frontières de domaine possibles, pas une obligation de créer quatorze modules vides.

## 6.5. Organisation recommandée du frontend

```text
frontend/
├── app/
│   ├── (public)/
│   │   ├── page.tsx
│   │   ├── discussions/
│   │   └── profils/
│   ├── (auth)/
│   │   ├── connexion/
│   │   └── inscription/
│   ├── (app)/
│   │   ├── fil/
│   │   ├── publier/
│   │   ├── questions/
│   │   ├── developpeurs/
│   │   ├── projets/
│   │   ├── notifications/
│   │   └── parametres/
│   ├── moderation/
│   └── layout.tsx
├── components/
│   ├── ui/
│   ├── layout/
│   ├── community/
│   ├── profile/
│   └── projects/
├── lib/
│   ├── api/
│   ├── auth/
│   ├── validators/
│   └── utils/
├── hooks/
├── types/
└── tests/
```

Les routes définitives peuvent évoluer selon la maquette, mais les responsabilités doivent rester séparées.

## 6.6. Contrat frontend/backend

- Toutes les routes REST sont préfixées par `/api/v1/`.
- Les données sont échangées en JSON, sauf envoi de fichiers.
- Les dates sont transmises en ISO 8601 et stockées de manière cohérente en UTC.
- Les erreurs utilisent des statuts HTTP explicites.
- Les listes sont paginées.
- Les filtres sont documentés.
- Chaque endpoint indique les permissions requises.
- Les changements incompatibles donnent lieu à une nouvelle version d'API ou à une migration documentée.

---

# 7. Modèle de données prévisionnel

Le modèle ci-dessous constitue le schéma logique de référence. Les noms de tables et les champs exacts pourront être ajustés pendant l'implémentation, mais les relations et contraintes doivent être conservées.

## 7.1. Comptes et profils

### `User`

| Champ | Type indicatif | Contraintes |
|---|---|---|
| id | UUID ou BIGINT | Clé primaire |
| username | VARCHAR | Unique, obligatoire |
| email | VARCHAR | Unique, obligatoire |
| password | Champ Django | Haché par Django |
| first_name | VARCHAR | Facultatif |
| last_name | VARCHAR | Facultatif |
| role | ENUM | MEMBER, MODERATOR, ADMIN |
| is_active | BOOLEAN | Défaut vrai |
| email_verified | BOOLEAN | Défaut faux si vérification activée |
| date_joined | DATETIME | Automatique |

Recommandation : définir un modèle utilisateur personnalisé dès le début du projet, avant les premières migrations, même si les champs supplémentaires semblent simples.

### `DeveloperProfile`

- `user_id` : OneToOne vers User ;
- `display_name` ;
- `bio` ;
- `avatar` ;
- `country_id` ;
- `city` ;
- `experience_level` ;
- `availability_status` ;
- `profile_visibility` ;
- `created_at`, `updated_at`.

### `Technology`

- `id` ;
- `name` unique ;
- `slug` unique ;
- `category` facultative ;
- `is_active`.

### `UserSkill`

- `user_id` ;
- `technology_id` ;
- `level` auto-déclaré ;
- `years_experience` facultatif ;
- `verification_status` : SELF_DECLARED, EVIDENCE_ADDED, PEER_REVIEWED ;
- `evidence_url` facultative ;
- contrainte unique sur `(user_id, technology_id)`.

### `SocialLink`

- `user_id` ;
- `platform` ;
- `url` ;
- `is_public`.

## 7.2. Contenus communautaires

### `Category`

- `id` ;
- `name` ;
- `slug` unique ;
- `description` ;
- `is_active` ;
- `sort_order`.

### `Tag`

- `id` ;
- `name` ;
- `slug` unique ;
- `is_active`.

### `Post`

- `id` ;
- `author_id` vers User ;
- `category_id` vers Category ;
- `type` : DISCUSSION, QUESTION, ARTICLE, ANNOUNCEMENT, PROJECT_UPDATE ;
- `title` ;
- `content` ;
- `status` : DRAFT, PUBLISHED, HIDDEN, DELETED ;
- `created_at` ;
- `updated_at` ;
- `published_at` ;
- relation ManyToMany vers Tag et Technology.

Index recommandés : `created_at`, `status`, `type`, `category_id`, `author_id` et champs utiles à la recherche.

### `Comment`

- `id` ;
- `post_id` ;
- `author_id` ;
- `parent_id` facultatif pour une réponse imbriquée limitée ;
- `content` ;
- `status` ;
- `created_at`, `updated_at`.

Pour le MVP, limiter la profondeur des réponses imbriquées à un niveau ou supprimer l'imbrication. Les fils de commentaires profonds augmentent la complexité de l'interface.

### `Answer`

- `id` ;
- `question_id` vers Post de type QUESTION ;
- `author_id` ;
- `content` ;
- `is_accepted` ;
- `status` ;
- `created_at`, `updated_at`.

### `Vote`

- `id` ;
- `user_id` ;
- `target_type` et `target_id`, ou tables de vote dédiées ;
- `value` : UPVOTE dans la version minimale ;
- `created_at` ;
- contrainte unique sur le membre et la cible.

Pour simplifier la cohérence, des tables séparées (`PostVote`, `AnswerVote`) sont préférables à un mécanisme générique lorsque l'équipe ne maîtrise pas encore les relations génériques Django.

### `Bookmark`

- `user_id` ;
- `post_id` ;
- `created_at` ;
- contrainte unique `(user_id, post_id)`.

## 7.3. Collaboration et projets

### `Project`

- `id` ;
- `owner_id` vers User ;
- `name` ;
- `slug` ;
- `short_description` ;
- `description` ;
- `objectives` ;
- `status` : IDEA, RECRUITING, IN_PROGRESS, PAUSED, COMPLETED, ARCHIVED ;
- `visibility` : PUBLIC, PRIVATE ;
- `repository_url` ;
- `demo_url` ;
- `created_at`, `updated_at`, `completed_at`.

### `ProjectMember`

- `project_id` ;
- `user_id` ;
- `role` : OWNER, MANAGER, CONTRIBUTOR, OBSERVER ;
- `joined_at` ;
- `status` : ACTIVE, LEFT, REMOVED ;
- contrainte unique adaptée au couple projet/utilisateur.

### `ProjectRoleNeed`

- `project_id` ;
- `role_name` ;
- `description` ;
- `required_technologies` ;
- `slots` ;
- `is_open`.

### `JoinRequest`

- `project_id` ;
- `user_id` ;
- `requested_role_id` facultatif ;
- `message` ;
- `status` : PENDING, ACCEPTED, REJECTED, WITHDRAWN ;
- `created_at`, `updated_at`, `reviewed_at` ;
- contrainte empêchant plusieurs demandes actives identiques.

### `ProjectTask`

- `id` ;
- `project_id` ;
- `title` ;
- `description` ;
- `assignee_id` facultatif ;
- `created_by_id` ;
- `status` : TODO, IN_PROGRESS, IN_REVIEW, DONE, BLOCKED ;
- `priority` : LOW, MEDIUM, HIGH ;
- `due_date` facultative ;
- `created_at`, `updated_at`.

### `Milestone` (P1)

- `project_id` ;
- `title` ;
- `description` ;
- `due_date` ;
- `status` ;
- `completed_at`.

### `ProjectUpdate` (P1)

- `project_id` ;
- `author_id` ;
- `content` ;
- `created_at`.

## 7.4. Réputation

### `Achievement`

- `name` ;
- `description` ;
- `icon_key` ;
- `rule_code` ;
- `is_active`.

### `UserAchievement`

- `user_id` ;
- `achievement_id` ;
- `awarded_at` ;
- contrainte unique `(user_id, achievement_id)`.

### `ContributionEvent`

- `user_id` ;
- `event_type` ;
- `object_type` ;
- `object_id` ;
- `points` ;
- `created_at`.

La réputation doit pouvoir être recalculée à partir des événements ou contrôlée par une logique cohérente ; éviter un score modifiable librement par le frontend.

## 7.5. Notifications et modération

### `Notification`

- `recipient_id` ;
- `type` ;
- `title` ;
- `message` ;
- `target_url` ou référence d'objet ;
- `is_read` ;
- `created_at`.

### `Report`

- `reporter_id` ;
- `target_type` ;
- `target_id` ;
- `reason` ;
- `details` ;
- `status` : PENDING, REVIEWING, ACTION_TAKEN, REJECTED, CLOSED ;
- `created_at`, `updated_at`.

### `ModerationAction`

- `report_id` facultatif ;
- `moderator_id` ;
- `target_type` ;
- `target_id` ;
- `action_type` ;
- `reason` ;
- `created_at`.

## 7.6. Modèles d'extension P2

- `Opportunity` et `OpportunityApplication` ;
- `MentorProfile`, `MentorshipRequest`, `MentorshipSession` ;
- `Community`, `CommunityMember`, `CommunityPost` ou relation post-communauté ;
- `Event`, `EventRegistration` ;
- `Conversation`, `ConversationParticipant`, `Message` ;
- `Follow` pour les abonnements ;
- `Block` pour les blocages.

Ces modèles sont décrits afin de préparer une évolution cohérente, mais ils ne doivent pas tous être implémentés pour valider le MVP.

## 7.7. Relations principales

```text
User 1 ─── 1 DeveloperProfile
User 1 ─── N Post
User 1 ─── N Comment
User 1 ─── N Answer
User N ─── N Technology (via UserSkill)
Post N ─── N Tag
Post N ─── N Technology
Post 1 ─── N Comment
Post (QUESTION) 1 ─── N Answer
User N ─── N Post (via Vote/Bookmark)
User 1 ─── N Project (owner)
Project 1 ─── N ProjectTask
Project N ─── N User (via ProjectMember)
Project 1 ─── N JoinRequest
User 1 ─── N Notification
User 1 ─── N Report (reporter)
```

---

# 8. API REST prévisionnelle

Les noms sont indicatifs mais doivent être stabilisés dans le contrat OpenAPI avant que le frontend et le backend travaillent en parallèle.

## 8.1. Convention générale

Base URL locale indicative : `http://localhost:8000/api/v1/`

Les endpoints ci-dessous supposent une version `/api/v1/`. Les réponses de liste doivent être paginées. Les permissions indiquées s'appliquent côté serveur.

## 8.2. Authentification et compte

| Méthode | Endpoint | Usage | Accès |
|---|---|---|---|
| POST | `/auth/register/` | Créer un compte | Public |
| POST | `/auth/login/` | Se connecter | Public |
| POST | `/auth/logout/` | Se déconnecter | Connecté |
| GET | `/auth/me/` | Compte courant | Connecté |
| POST | `/auth/password/reset/` | Demander une réinitialisation | Public |
| POST | `/auth/password/reset/confirm/` | Confirmer la réinitialisation | Public avec jeton valide |

## 8.3. Profils et référentiels

| Méthode | Endpoint | Usage |
|---|---|---|
| GET | `/profiles/` | Rechercher/lister les profils publics |
| GET | `/profiles/{username}/` | Consulter un profil |
| PATCH | `/profiles/me/` | Modifier son profil |
| PUT/PATCH | `/profiles/me/skills/` | Gérer ses compétences |
| GET | `/technologies/` | Lister les technologies |
| GET | `/categories/` | Lister les catégories |
| GET | `/tags/` | Rechercher les tags |

## 8.4. Publications et échanges

| Méthode | Endpoint | Usage |
|---|---|---|
| GET | `/posts/` | Fil communautaire et filtres |
| POST | `/posts/` | Créer une publication |
| GET | `/posts/{id}/` | Consulter une publication |
| PATCH | `/posts/{id}/` | Modifier sa publication |
| DELETE | `/posts/{id}/` | Suppression logique autorisée |
| POST | `/posts/{id}/comments/` | Commenter |
| GET | `/posts/{id}/comments/` | Lister les commentaires |
| POST | `/posts/{id}/vote/` | Voter/retirer son vote |
| POST | `/posts/{id}/bookmark/` | Ajouter/retirer un favori (P1) |
| GET | `/questions/` | Lister les questions |
| POST | `/questions/{id}/answers/` | Répondre |
| POST | `/answers/{id}/accept/` | Accepter une réponse (P1) |
| POST | `/answers/{id}/vote/` | Voter pour une réponse |

## 8.5. Recherche

| Méthode | Endpoint | Usage |
|---|---|---|
| GET | `/search/` | Recherche générale |
| GET | `/search/posts/` | Recherche de contenus |
| GET | `/search/users/` | Recherche de profils |
| GET | `/search/projects/` | Recherche de projets |

Exemples de paramètres : `q`, `type`, `category`, `technology`, `country`, `availability`, `ordering`, `page`.

## 8.6. Projets et collaboration

| Méthode | Endpoint | Usage |
|---|---|---|
| GET | `/projects/` | Lister les projets publics |
| POST | `/projects/` | Créer un projet |
| GET | `/projects/{slug}/` | Détail d'un projet |
| PATCH | `/projects/{slug}/` | Modifier un projet selon rôle |
| POST | `/projects/{id}/join-requests/` | Demander à rejoindre |
| GET | `/projects/{id}/join-requests/` | Lister les demandes pour le propriétaire |
| POST | `/join-requests/{id}/accept/` | Accepter une demande |
| POST | `/join-requests/{id}/reject/` | Refuser une demande |
| GET | `/projects/{id}/members/` | Lister les membres |
| POST | `/projects/{id}/tasks/` | Créer une tâche |
| PATCH | `/tasks/{id}/` | Modifier une tâche |

## 8.7. Notifications, signalements et administration

| Méthode | Endpoint | Usage |
|---|---|---|
| GET | `/notifications/` | Lister les notifications du membre |
| POST | `/notifications/{id}/read/` | Marquer comme lue |
| POST | `/reports/` | Créer un signalement |
| GET | `/moderation/reports/` | File des signalements |
| POST | `/moderation/reports/{id}/action/` | Traiter un signalement |

Les routes d'administration doivent appliquer une permission stricte au rôle administrateur ou modérateur selon l'action.

## 8.8. Format de réponse et erreurs

Format de succès recommandé pour une ressource :

```json
{
  "id": "resource-id",
  "title": "Titre de l'élément",
  "created_at": "2026-11-13T10:30:00Z"
}
```

Format d'erreur recommandé :

```json
{
  "detail": "Le contenu fourni est invalide.",
  "code": "validation_error",
  "errors": {
    "title": ["Ce champ est obligatoire."]
  }
}
```

Pour les listes, adopter le format de pagination Django REST Framework ou un format standard documenté, sans mélanger plusieurs conventions.

---

# 9. Interfaces et expérience utilisateur

## 9.1. Principes UX

- L'utilisateur doit comprendre immédiatement la fonction de chaque page.
- Les actions principales doivent être visibles sans surcharge visuelle.
- Les formulaires doivent demander uniquement les informations utiles à l'action en cours.
- Les états vides doivent expliquer ce que l'utilisateur peut faire.
- Les erreurs doivent être compréhensibles et actionnables.
- Les contenus communautaires doivent rester lisibles sur petit écran.
- Les composants doivent être réutilisables et cohérents.

## 9.2. Arborescence des pages du MVP

| Page | Fonction principale | Priorité |
|---|---|---|
| Accueil public | Présenter la plateforme et les contenus publics | P0 |
| Inscription | Créer un compte | P0 |
| Connexion | Accéder au compte | P0 |
| Fil communautaire | Découvrir les discussions | P0 |
| Détail d'une publication | Lire et participer | P0 |
| Créer une publication | Lancer une discussion ou question | P0 |
| Profil public | Découvrir un membre | P0 |
| Mon profil | Modifier ses informations | P0 |
| Annuaire développeurs | Rechercher des profils | P0 simple / P1 avancé |
| Liste des projets | Découvrir les projets | P0 |
| Détail d'un projet | Consulter équipe et progression | P0 |
| Créer un projet | Publier un appel à collaboration | P0 |
| Demandes reçues | Gérer les candidatures | P0 |
| Espace projet | Gérer les tâches simples | P0 |
| Notifications | Consulter ses alertes | P1 |
| Modération | Traiter les signalements | P0 au minimum |

## 9.3. Navigation recommandée

Navigation principale possible :

- Fil ;
- Questions ;
- Développeurs ;
- Projets ;
- Opportunités (P2) ;
- Notifications ;
- Profil.

Sur mobile, utiliser une navigation compacte et maintenir l'accès à la création d'une publication.

## 9.4. Design system

L'identité graphique doit être définie avant la multiplication des pages. Recommandations :

- identité visuelle moderne et professionnelle ;
- références africaines subtiles, sans tomber dans des clichés visuels ;
- couleurs suffisamment contrastées ;
- typographie très lisible ;
- composants cohérents pour les boutons, cartes, champs, badges, menus, alertes et modales ;
- distinction claire entre catégories, technologies, statuts et rôles ;
- aucun texte essentiel intégré uniquement dans une image.

Les couleurs, le logo et la charte définitive restent à valider par l'équipe.

## 9.5. États d'interface à prévoir

Pour chaque page dynamique :

- chargement ;
- chargement partiel si possible ;
- succès ;
- erreur serveur ;
- absence de résultat ;
- absence de permission ;
- contenu supprimé ou indisponible ;
- session expirée.

---

# 10. Exigences non fonctionnelles

## 10.1. Performance

- Les pages principales doivent se charger rapidement sur une connexion moyenne.
- Les listes sont paginées côté serveur.
- Les images sont redimensionnées et compressées.
- Les requêtes ORM doivent éviter le problème N+1 avec `select_related` et `prefetch_related` lorsque nécessaire.
- Les endpoints coûteux doivent être indexés et surveillés.
- La première version ne nécessite pas de cache distribué obligatoire.

## 10.2. Disponibilité et robustesse

- Les erreurs inattendues ne doivent pas exposer de trace technique à l'utilisateur.
- Les migrations de base de données doivent être versionnées.
- Les données essentielles doivent être sauvegardées avant une mise en production réelle.
- Les opérations sensibles doivent être transactionnelles.
- Le système doit gérer proprement les doubles soumissions et les requêtes répétées.

## 10.3. Sécurité

- HTTPS obligatoire en environnement déployé.
- Hachage des mots de passe par les mécanismes Django.
- Protection CSRF lorsque l'authentification par cookie/session est utilisée.
- Cookies `HttpOnly`, `Secure` en production et politique `SameSite` adaptée.
- CORS limité aux origines autorisées.
- Validation serveur de toutes les entrées.
- Contrôle d'accès sur chaque ressource sensible.
- Protection contre les attaques XSS, injections SQL, CSRF, brute force et IDOR.
- Limitation de débit sur connexion, inscription, publication et messagerie.
- Gestion sécurisée des secrets par variables d'environnement.
- Journaux sans mot de passe, jeton, secret ou donnée sensible inutile.
- Fichiers uploadés : taille, type, extension et contenu contrôlés.
- Dépendances maintenues et verrouillées.

### Choix d'authentification recommandé

Pour le MVP web, privilégier une authentification par session/cookie sécurisée si le frontend et le backend peuvent être servis sous un même domaine ou une configuration maîtrisée. Si une authentification par jeton est retenue, utiliser des jetons à durée de vie limitée et ne pas stocker les jetons sensibles dans `localStorage`.

Le choix définitif doit être testé avec Next.js, Django et la configuration de domaines/CORS réelle. Ne pas mélanger plusieurs mécanismes improvisés.

La documentation de DRF rappelle que l'authentification identifie l'utilisateur, tandis que les permissions décident si l'action est autorisée : [Authentification DRF](https://www.django-rest-framework.org/api-guide/authentication/) et [Permissions DRF](https://www.django-rest-framework.org/api-guide/permissions/).

## 10.4. Confidentialité

- Ne collecter que les informations utiles.
- Ne pas demander d'adresse personnelle précise.
- Permettre de contrôler la visibilité du profil lorsque prévu.
- Ne jamais exposer e-mail, téléphone ou données privées par défaut.
- Prévoir une procédure de désactivation/suppression du compte.
- Définir une politique de conservation des signalements et journaux.
- Informer les membres des données publiques de leur profil.

## 10.5. Accessibilité

- Contraste suffisant entre texte et arrière-plan.
- Navigation clavier pour les actions principales.
- Libellés explicites sur les champs.
- Textes alternatifs sur les images utiles.
- Indication visuelle et textuelle des erreurs.
- Ne pas utiliser la couleur comme seul moyen de communiquer un statut.

## 10.6. Compatibilité

Prendre en charge les versions récentes des navigateurs courants : Chrome, Edge, Firefox et Safari, avec une attention particulière aux navigateurs mobiles Android et iOS.

## 10.7. Faible connectivité

- Limiter les images lourdes.
- Éviter les animations coûteuses.
- Garder les pages principales sobres.
- Prévoir un retour clair lorsque la connexion est perdue.
- Éviter les envois multiples involontaires.
- Préparer une évolution PWA, sans en faire une condition du MVP.

---

# 11. Règles métier transversales

1. Toute action de création ou modification doit être validée par le backend.
2. Un membre ne peut modifier que ses propres contenus, sauf permission particulière.
3. Les administrateurs et modérateurs disposent de permissions distinctes et journalisées.
4. Un contenu supprimé ou masqué doit conserver une trace minimale lorsque nécessaire pour l'intégrité des échanges et la modération.
5. Les compteurs de votes, commentaires et membres doivent être dérivés de données fiables, pas acceptés depuis le frontend.
6. Les relations Many-to-Many doivent avoir des contraintes évitant les doublons.
7. Un utilisateur ne peut pas être membre actif deux fois du même projet.
8. Une demande de rejoindre un projet ne peut être acceptée si le projet est fermé ou archivé.
9. Une tâche ne peut être assignée qu'à un membre actif du projet.
10. Les données privées ne doivent pas être renvoyées par les endpoints publics.
11. Les statuts sont contrôlés par des transitions autorisées.
12. Les opérations qui modifient plusieurs objets liés doivent être exécutées dans une transaction.
13. Les dates sont stockées et échangées avec un fuseau cohérent ; l'interface les affiche dans le fuseau de l'utilisateur.
14. Toute action de modération est traçable.
15. Les contenus externes et liens fournis par les membres sont considérés comme non fiables.

---

# 12. Tests et stratégie qualité

## 12.1. Tests backend

À couvrir au minimum :

- inscription valide et invalide ;
- unicité e-mail/nom d'utilisateur ;
- accès anonyme et authentifié ;
- permissions de modification/suppression ;
- publication, commentaire, réponse et vote ;
- impossibilité de voter plusieurs fois ;
- acceptation d'une réponse par le bon utilisateur ;
- recherche et pagination ;
- création d'un projet ;
- demande de rejoindre ;
- acceptation/refus par le propriétaire ;
- affectation d'une tâche à un membre du projet ;
- signalement et action de modération ;
- confidentialité des champs de profil.

## 12.2. Tests frontend

- rendu des pages principales ;
- validation des formulaires ;
- affichage des états de chargement et d'erreur ;
- navigation ;
- affichage responsive ;
- affichage conditionnel des actions selon le rôle ;
- gestion d'une session expirée ;
- confirmation avant suppression ou action destructive.

## 12.3. Tests end-to-end prioritaires

1. Un visiteur crée un compte et complète son profil.
2. Il publie une question.
3. Un autre membre répond.
4. Le premier membre consulte la réponse.
5. Un membre crée un projet ouvert à la collaboration.
6. Un autre membre demande à rejoindre le projet.
7. Le propriétaire accepte la demande.
8. Le nouveau membre consulte le projet et met à jour une tâche.
9. Un membre signale un contenu.
10. Le modérateur traite le signalement.

## 12.4. Définition de terminé (Definition of Done)

Une fonctionnalité n'est considérée comme terminée que si :

- le modèle et la migration sont créés si nécessaire ;
- l'API fonctionne et valide les entrées ;
- les permissions sont appliquées côté backend ;
- l'interface gère succès, erreur et chargement ;
- les tests essentiels passent ;
- le comportement mobile a été vérifié ;
- la documentation API est mise à jour ;
- aucun secret ou donnée de démonstration sensible n'est commité.

---

# 13. Déploiement et environnement de développement

## 13.1. Environnements

- **Local :** environnement de développement individuel.
- **Intégration :** environnement partagé de test de l'équipe.
- **Démonstration :** environnement stable réservé au jury et à la présentation.

## 13.2. Variables d'environnement

Exemples de variables, sans valeurs secrètes dans Git :

```env
DJANGO_SECRET_KEY=
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=
DATABASE_URL=
CORS_ALLOWED_ORIGINS=
CSRF_TRUSTED_ORIGINS=
EMAIL_HOST=
EMAIL_PORT=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
NEXT_PUBLIC_API_BASE_URL=
```

Le nom précis des variables peut être adapté à la configuration choisie.

## 13.3. Docker Compose

Pour le développement, Docker Compose peut orchestrer :

- backend Django ;
- PostgreSQL ;
- frontend Next.js ;
- Redis uniquement si une tâche asynchrone ou un cache le justifie.

Ne pas ajouter une infrastructure complexe sans besoin fonctionnel démontré.

## 13.4. Déploiement

Le déploiement doit comporter :

- service frontend ;
- service backend ;
- base PostgreSQL persistante ;
- configuration HTTPS ;
- migrations exécutées de manière contrôlée ;
- création d'un compte administrateur ;
- données de démonstration ;
- logs exploitables ;
- procédure de sauvegarde/restauration minimale.

## 13.5. Données de démonstration

Préparer des données fictives cohérentes :

- membres avec profils variés ;
- technologies et catégories ;
- discussions réalistes ;
- questions et réponses ;
- projets ouverts à la collaboration ;
- tâches de projets ;
- signalements de test.

Ne pas utiliser de faux témoignages présentés comme de vrais utilisateurs. Les données de démonstration doivent être identifiées comme fictives si cela peut prêter à confusion.

---

# 14. Organisation du travail et pilotage du hackathon

La durée et la taille exactes de l'équipe n'étant pas précisées ici, le découpage est relatif et adaptable.

## 14.1. Rôles d'équipe conseillés

| Rôle | Responsabilités |
|---|---|
| Chef de projet / Product Owner | Priorités, arbitrages, suivi du périmètre, cohérence produit, préparation de la démonstration |
| Référent backend | Modèles, API, permissions, logique métier, migrations et tests backend |
| Référent frontend | Architecture Next.js, composants, intégration API, responsive et états UI |
| UX/UI | Parcours, wireframes, design system, cohérence visuelle et accessibilité |
| QA / intégration | Tests fonctionnels, scénarios de recette, validation sur différents écrans et stabilité de la démo |

Dans une petite équipe, une personne peut porter plusieurs rôles. Chaque module doit néanmoins avoir un responsable clairement identifié.

## 14.2. Découpage en phases

### Phase 1 – Cadrage et arbitrage

- vérifier les consignes exactes du concours ;
- valider le public cible ;
- valider la proposition de valeur ;
- fixer le périmètre P0 ;
- lister les écrans et les endpoints ;
- désigner les responsables de modules.

**Livrables :** périmètre gelé, backlog priorisé, parcours validés.

### Phase 2 – Conception et socle technique

- créer les dépôts ;
- configurer Django et Next.js ;
- configurer PostgreSQL ;
- créer le modèle utilisateur ;
- définir les conventions API ;
- créer le design system initial ;
- établir l'environnement partagé.

**Livrables :** application qui démarre, base connectée, authentification de base, contrat API.

### Phase 3 – Développement du cœur communautaire

- profils ;
- catégories et technologies ;
- fil communautaire ;
- publications ;
- commentaires et réponses ;
- votes ;
- recherche simple.

**Livrable :** boucle complète de discussion démontrable.

### Phase 4 – Collaboration et projets

- création de projets ;
- rôles recherchés ;
- demandes pour rejoindre ;
- validation des demandes ;
- espace projet ;
- tâches simples.

**Livrable :** passage démontrable de la discussion à la collaboration.

### Phase 5 – Qualité, sécurité et modération

- signalements ;
- modération minimale ;
- vérification des permissions ;
- tests des parcours ;
- corrections responsive ;
- données de démonstration.

**Livrable :** MVP stabilisé.

### Phase 6 – Présentation

- préparer un scénario de démonstration ;
- vérifier le réseau et les comptes de démonstration ;
- préparer une courte présentation de la problématique et de la proposition de valeur ;
- présenter les choix techniques et les limites connues ;
- montrer les évolutions futures sans les faire passer pour des fonctionnalités déjà livrées.

## 14.3. Répartition indicative du temps

| Activité | Part indicative |
|---|---:|
| Cadrage et conception | 10 % |
| UX/UI et socle technique | 15 % |
| Développement du MVP | 50 % |
| Tests, intégration et corrections | 15 % |
| Préparation de la démonstration | 10 % |

Si le concours est très court, réduire les extensions et non le temps de test. Une application qui fonctionne uniquement sur l'ordinateur du développeur n'est pas un MVP.

## 14.4. Règles de gestion de projet

- Un backlog unique doit être utilisé.
- Chaque tâche possède un responsable et un critère d'acceptation.
- Les branches Git doivent être courtes et régulièrement intégrées.
- Les migrations backend doivent être coordonnées.
- Les endpoints doivent être documentés avant l'intégration frontend.
- Les décisions structurantes sont consignées.
- Une fonctionnalité P1 ne doit pas être commencée si une fonctionnalité P0 essentielle est encore cassée.
- Prévoir une période de gel des fonctionnalités avant la démonstration.

---

# 15. Indicateurs de réussite

Les métriques suivantes permettent d'évaluer le produit au-delà de son apparence.

## 15.1. Activation

- taux de création de profil après inscription ;
- proportion de membres ayant consulté ou publié une discussion ;
- délai entre inscription et première interaction.

## 15.2. Qualité des échanges

- nombre de questions recevant au moins une réponse ;
- délai médian avant première réponse ;
- proportion de questions avec réponse acceptée (quand la fonction existe) ;
- proportion de contenus signalés et modérés.

## 15.3. Collaboration

- nombre de projets publiés ;
- nombre de demandes de collaboration ;
- taux d'acceptation des demandes ;
- nombre de projets ayant au moins deux membres actifs ;
- nombre de projets terminés ou présentant une démonstration.

## 15.4. Qualité technique du MVP

- parcours critiques exécutables sans erreur bloquante ;
- tests essentiels réussis ;
- aucune permission critique uniquement contrôlée côté frontend ;
- application responsive ;
- déploiement accessible pendant la démonstration.

Ne pas inventer des objectifs chiffrés sans connaître la durée du concours et la taille de la communauté initiale. Les premières métriques servent surtout à comprendre l'usage.

---

# 16. Risques et mesures de réduction

| Risque | Impact | Mesure de réduction |
|---|---|---|
| Périmètre trop large | MVP incomplet | Protéger P0, repousser P2/P3 |
| Confusion entre React, Vue et Next.js | Complexité et incohérence | Utiliser React avec Next.js, exclure Vue du frontend initial |
| Plateforme vide | Faible démonstration de valeur | Préparer des données fictives cohérentes et recruter un premier noyau de membres |
| Discussions de faible qualité | Perte d'utilité | Catégories, tags, recherche, règles communautaires et modération |
| Faux profils ou fausses compétences | Perte de confiance | Distinguer compétences déclarées et preuves |
| Fausses offres d'emploi ou arnaques | Risque pour les membres | Vérification, signalement, statut de publication et modération |
| Permissions mal conçues | Fuite ou modification non autorisée | Permissions serveur et tests d'accès |
| Dépendance à GitHub | Blocage de la collaboration | Utiliser les liens externes comme complément, pas comme dépendance obligatoire |
| Connexion faible | Mauvaise expérience | Interface légère, pagination et images optimisées |
| Conflits Git ou migrations | Retards | Responsables de modules, branches courtes, intégration régulière |
| Démonstration instable | Mauvaise évaluation | Environnement dédié, comptes test et scénario répété |
| Trop de temps consacré au design | Fonctionnalités inachevées | Design system simple et priorité aux parcours fonctionnels |

---

# 17. Scénario de démonstration devant le jury

La démonstration doit montrer une histoire cohérente plutôt qu'une succession de pages.

## Scénario recommandé

1. Présenter la page d'accueil et expliquer la fragmentation actuelle des échanges techniques.
2. Se connecter avec un profil développeur déjà préparé.
3. Montrer le profil et ses compétences déclarées.
4. Ouvrir une question technique et montrer les réponses.
5. Publier une discussion ou une question en direct si le temps le permet.
6. Rechercher un développeur à partir d'une technologie.
7. Ouvrir un projet qui cherche un collaborateur.
8. Envoyer une demande pour rejoindre le projet.
9. Se connecter avec le propriétaire et accepter la demande.
10. Ouvrir l'espace projet, montrer les membres et attribuer une tâche.
11. Terminer par la vision d'évolution : opportunités, mentorat, communautés et événements.

## Message à faire retenir

La plateforme ne veut pas être un réseau social généraliste supplémentaire. Elle organise les échanges techniques et facilite la transformation de ces échanges en collaborations et réalisations visibles.

---

# 18. Critères de recette et validation finale

Le MVP est considéré comme acceptable lorsque les conditions suivantes sont réunies.

## 18.1. Fonctionnel

- [ ] Un utilisateur peut créer un compte et se connecter.
- [ ] Un membre peut compléter et modifier son profil.
- [ ] Un visiteur peut consulter les contenus publics.
- [ ] Un membre peut publier une discussion.
- [ ] Un membre peut publier une question.
- [ ] Un autre membre peut répondre à une question.
- [ ] Les votes ne peuvent pas être dupliqués.
- [ ] Les publications peuvent être filtrées et recherchées.
- [ ] Un membre peut créer un projet ouvert à la collaboration.
- [ ] Un membre peut demander à rejoindre un projet.
- [ ] Le propriétaire peut accepter ou refuser une demande.
- [ ] Les membres autorisés peuvent gérer les tâches simples du projet.
- [ ] Un utilisateur peut signaler un contenu.
- [ ] Un modérateur peut traiter un signalement.
- [ ] Les pages principales sont utilisables sur mobile.

## 18.2. Sécurité

- [ ] Les permissions sont vérifiées côté backend.
- [ ] Les secrets ne sont pas présents dans le dépôt Git.
- [ ] Les mots de passe ne sont jamais stockés en clair.
- [ ] Les données privées ne sont pas exposées publiquement.
- [ ] Les actions de modération sont journalisées.
- [ ] Les entrées utilisateur sont validées et les contenus affichés de manière sûre.

## 18.3. Technique

- [ ] Les migrations sont versionnées et exécutables.
- [ ] Le frontend communique avec le backend via l'API documentée.
- [ ] Les listes sont paginées.
- [ ] Les erreurs API sont traitées par le frontend.
- [ ] Les tests critiques passent.
- [ ] Le déploiement de démonstration est accessible.
- [ ] Les comptes et données de démonstration sont prêts.

---

# 19. Décisions restant à valider avant le premier sprint

Ces points ne bloquent pas la rédaction du cahier, mais doivent être décidés par l'équipe avant de figer les modèles et l'interface.

1. **Nom définitif et identité visuelle :** AfriDev Community est un nom de travail.
2. **Public de lancement :** communauté francophone africaine ou communauté panafricaine bilingue dès la première version.
3. **Règlement CADEV :** durée, livrables, contraintes techniques et critères de notation officiels.
4. **Authentification :** sessions/cookies sécurisés ou authentification par jetons, selon le déploiement retenu.
5. **Visibilité des projets :** projets tous publics dans le MVP ou prise en charge de projets privés dès la première version.
6. **Suppression de compte :** désactivation, anonymisation ou suppression selon les contraintes légales et opérationnelles.
7. **Hébergement et nom de domaine :** fournisseur, budget, région et configuration.
8. **Taille de l'équipe et répartition réelle des responsabilités.**
9. **Charte de modération :** règles communautaires et procédure d'appel en cas de sanction.
10. **Politique de vérification :** niveau de contrôle exigé pour les partenaires et annonces d'opportunités.

## 19.1. Hypothèses retenues par défaut pour démarrer

En l'absence d'une décision contraire de l'équipe :

- lancement francophone, architecture prête pour l'anglais ;
- comptes publics avec profil partiellement configurable ;
- projets publics dans le MVP ;
- Django REST Framework comme API unique ;
- React avec Next.js et TypeScript côté frontend ;
- PostgreSQL comme base principale ;
- pas de messagerie temps réel, d'IA ni d'application native dans le MVP ;
- données de démonstration fictives ;
- modération manuelle par administrateur/modérateur.

---

# 20. Références techniques

Les références ci-dessous servent de base documentaire pour l'implémentation. Elles ne remplacent pas la lecture de la documentation correspondant aux versions réellement figées dans le dépôt.

- [Django – versions prises en charge et calendrier de support](https://www.djangoproject.com/download/)
- [Django – documentation officielle](https://docs.djangoproject.com/)
- [Django REST Framework – documentation générale](https://www.django-rest-framework.org/)
- [Django REST Framework – authentification](https://www.django-rest-framework.org/api-guide/authentication/)
- [Django REST Framework – permissions](https://www.django-rest-framework.org/api-guide/permissions/)
- [Django REST Framework – pagination](https://www.django-rest-framework.org/api-guide/pagination/)
- [Next.js – React et Next.js](https://nextjs.org/learn/react-foundations/what-is-react-and-nextjs)
- [Next.js – guide App Router](https://nextjs.org/learn)
- [PostgreSQL – documentation officielle](https://www.postgresql.org/docs/)

---

# Conclusion

AfriDev Community doit d'abord réussir une chose : offrir un espace où les développeurs africains peuvent réellement échanger, obtenir de l'aide et retrouver des contenus utiles. Sa valeur supplémentaire vient de sa capacité à connecter ces échanges à des personnes, des équipes et des projets.

Le périmètre est volontairement ambitieux dans sa vision, mais séquencé dans son exécution. Pour le hackathon, la réussite ne dépendra pas du nombre de modules annoncés. Elle dépendra surtout de la qualité de la boucle principale : **un membre publie, la communauté répond, des développeurs se découvrent et une collaboration peut démarrer**.

**Règle finale de pilotage : livrer un P0 cohérent et démontrable avant de toucher aux extensions P1, P2 ou P3.**
