# ADR 0006 — Choix structurants des extensions P2

- **Statut :** accepté
- **Date :** 2026-11-14
- **Exigences liées :** modules L, M, N, O, P, §19.1, §19 (point 10)

## Décisions

### Opportunités et partenaires (module L)

- Toute annonce exige une **source officielle** (`source_url`, http/https).
- Une organisation n'est « partenaire vérifié » qu'après **vérification par un administrateur**
  (action journalisée). Seuls ses membres publient sans validation ; toute autre annonce passe
  par une **file de validation** de la modération (`PENDING_REVIEW` → `PUBLISHED` / `REJECTED`).
- Modifier une annonce publiée la renvoie en validation si le publieur n'est pas vérifié.
- L'expiration est **calculée** à partir de la date limite (`is_expired`) : aucune tâche
  planifiée n'est nécessaire, les offres expirées sont masquées par défaut et signalées.
- Pas de paiement ni de recrutement de bout en bout : un membre exprime une candidature ou une
  demande d'information, visible du seul publieur.

### Mentorat (module M)

- Démarche volontaire : profil de mentor déclaré, demande avec objectif explicite, jamais
  d'acceptation automatique, capacité maximale de mentorés actifs.
- Sessions, liens de réunion, notes et retours visibles des **seuls participants**.

### Communautés et événements (modules N, O)

- Une communauté garde **toujours au moins un responsable** (départ ou rétrogradation du dernier
  refusés). Publier dans une communauté exige d'en être membre.
- La **modération locale** retire une publication du seul fil de la communauté (journalisée,
  auteur informé) ; la modération globale reste prioritaire.
- Le lien de participation d'un événement n'est communiqué qu'aux inscrits ; la capacité est
  protégée par un verrou sur l'événement.
- Les rappels sont envoyés par `python manage.py send_event_reminders`, à planifier (cron) :
  aucun broker de tâches n'est ajouté (§13.3).

### Messagerie (module P)

- **Pas de temps réel** (§19.1) : consultation classique et compteur de non-lus.
- Une conversation par couple de membres ; blocage effectif dans les deux sens.
- Texte brut uniquement, trois liens au plus, schémas http/https seuls ; limite de débit
  `messaging`.
- Les conversations ne sont lisibles ni dans l'API ni dans l'admin par des tiers. **Procédure
  documentée** : seul un message **signalé par un participant** est présenté à la modération
  (aperçu du seul message), qui peut le masquer.

### Modération générique

Chaque type de cible P2 s'enregistre dans le registre `moderation.targets` avec son propre
comportement de masquage (`flag_hider`). Le workflow, la journalisation et les notifications
restent identiques pour toutes les cibles.

## Conséquences

- Aucun service supplémentaire (Redis, Celery, WebSocket) : la pile reste celle du MVP.
- Une évolution temps réel (P3) pourra s'appuyer sur les mêmes modèles et services.
