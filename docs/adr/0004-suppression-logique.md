# ADR 0004 — Suppression logique et transitions de statut contrôlées

- **Statut :** accepté
- **Date :** 2026-11-14
- **Exigences liées :** §C.3, §D.2, §Q.4, §11.4, §11.11, §11.14

## Contexte

Un contenu supprimé par son auteur ou masqué par la modération doit disparaître des espaces
publics tout en restant traçable et restaurable par un administrateur.

## Décision

1. Les publications, commentaires et réponses portent un `status` :
   `DRAFT` (publications seulement), `PUBLISHED`, `HIDDEN`, `DELETED`. Aucune suppression
   physique depuis l'API ni depuis l'admin.
2. Deux managers par modèle :
   - `all_objects` (manager par défaut) : toutes les lignes, utilisé par l'admin, les
     migrations et la modération ;
   - `objects` : exclut `HIDDEN` et `DELETED`.
   Les sélecteurs publics (`selectors.feed`, `visible_answers`…) filtrent explicitement sur
   `PUBLISHED`. La recherche part toujours de ces sélecteurs.
3. Les changements de statut passent par une table de transitions (`CONTENT_TRANSITIONS`) et par
   `common.transitions.ensure_transition`. Une transition absente de la table renvoie
   `409 invalid_transition`.

| De \ Vers | PUBLISHED | HIDDEN | DELETED |
|---|---|---|---|
| DRAFT | auteur | — | auteur |
| PUBLISHED | — | modération | auteur, modération |
| HIDDEN | modération | — | modération |
| DELETED | **administrateur** | — | — |

4. Un contenu `HIDDEN` ou `DELETED` n'est plus modifiable par son auteur (`409 content_removed`).
   L'auteur voit encore sa publication masquée (pour comprendre la décision), pas sa publication
   supprimée.
5. Un commentaire retiré qui possède encore des réponses visibles est renvoyé comme emplacement
   vide (`is_removed: true`, sans auteur ni contenu) pour ne pas casser le fil.
6. Une réponse retirée perd son statut de réponse acceptée.

Le même principe (statut + table de transitions) est appliqué aux signalements, aux demandes
pour rejoindre un projet, aux tâches et aux projets.

## Conséquences

- Les clés étrangères vers les auteurs sont en `PROTECT` : un compte n'est jamais supprimé
  physiquement, il est désactivé (voir ADR 0001).
- Toute action de modération est journalisée par le module `moderation`, seul autorisé à
  appeler `community.services.moderate_status`.
