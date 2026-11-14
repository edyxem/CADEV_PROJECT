# ADR 0003 — Votes en tables dédiées (`PostVote`, `AnswerVote`)

- **Statut :** accepté
- **Date :** 2026-11-14
- **Exigences liées :** P0-06, §7.2 (`Vote`), §D.2, §11.5, §11.6

## Contexte

Le cahier des charges laisse le choix entre une table générique (`target_type`, `target_id`) et
des tables dédiées, en recommandant ces dernières pour la cohérence.

## Décision

- Deux tables : `PostVote(user, post)` et `AnswerVote(user, answer)`, chacune avec une
  `UniqueConstraint` sur le couple (membre, cible) et de vraies clés étrangères.
- Vote positif uniquement (pas de vote négatif dans le MVP).
- `POST …/vote/` sans corps **bascule** l'état ; `{"active": true|false}` **fixe** l'état de façon
  idempotente ; `DELETE …/vote/` retire le vote. La réponse renvoie toujours
  `{"voted", "vote_count"}` recalculé depuis la base.
- Le service verrouille la ligne de la cible (`select_for_update`) pour sérialiser les requêtes
  concurrentes ; la contrainte d'unicité reste le dernier rempart (une `IntegrityError` est
  absorbée et l'état final reste correct).
- Voter pour son propre contenu est refusé (`409 self_vote`) : cela prépare un calcul de
  réputation non manipulable.
- Les compteurs exposés (`vote_count`, `comment_count`, `answer_count`) sont des sous-requêtes
  annotées ; aucun compteur n'est stocké ni accepté depuis le client.

## Conséquences

- Intégrité référentielle garantie par PostgreSQL (suppression en cascade, pas d'orphelins).
- Ajouter un type de cible votable implique une nouvelle table : coût assumé, le nombre de cibles
  reste faible.
- Les paliers de votes (1, 5, 10, 25, 50, 100) déclenchent une notification à l'auteur, jamais à
  chaque vote.
