# Réputation et badges — règles de calcul

Module `apps.reputation` — exigences module I (§4.9), §7.4.

## Principes

1. La réputation valorise la **participation réelle et vérifiable**, pas le volume de
   publications ni le nombre de « j'aime ».
2. **Aucun point n'est accordé à la création d'un compte.**
3. Le score est la somme des `ContributionEvent` d'un membre. Ces événements sont **dérivés des
   données sources** (réponses, votes, tâches…) par `reputation.services.sync_user` : ils ne
   sont jamais saisis, ni par le frontend ni par un administrateur, et peuvent être
   intégralement recalculés (`python manage.py recompute_reputation`).
4. Un contenu masqué ou supprimé, un vote retiré, une acceptation annulée ou un compte votant
   désactivé font **disparaître** les points correspondants au recalcul suivant.
5. Le score n'est **pas une preuve de compétence** ; l'API le rappelle (`explanation`).

## Barème

| Événement | Points | Plafond | Source |
|---|---:|---|---|
| Réponse acceptée | 15 | — | réponse publiée acceptée par l'auteur de la question |
| Vote utile reçu sur une réponse | 2 | 10 votes comptés par réponse | votes de comptes actifs |
| Vote utile reçu sur une publication | 1 | 10 votes comptés par publication | votes de comptes actifs |
| Tutoriel / article publié | 5 | 20 articles | publication de type `ARTICLE` publiée |
| Tâche de projet terminée | 3 | 100 tâches | tâche `DONE` dont le membre est l'assigné |
| Projet terminé | 20 | — | projet `COMPLETED`, non masqué, dont le membre est membre actif |
| Recommandation reçue | 5 | 20 recommandations | recommandation d'un compte actif |
| Mentorat terminé (P2) | 10 | 50 mentorats | demande de mentorat `COMPLETED`, côté mentor |

Garde-fous anti-abus :

- voter pour son propre contenu est impossible (`409 self_vote`) ;
- un membre ne peut ni se recommander lui-même (contrainte en base) ni recommander deux fois la
  même personne ; un contexte concret d'au moins 30 caractères est exigé ;
- les plafonds par objet empêchent qu'un seul contenu « gonfle » un score ;
- les limites de débit (`THROTTLE_*`) freinent les actions automatisées.

## Badges

Un badge est attribué dès que le nombre d'événements d'un type atteint un seuil, et **retiré**
si ce seuil n'est plus atteint (contenu retiré par la modération, par exemple).

| Code | Nom | Règle |
|---|---|---|
| `premiere-solution` | Première solution | ≥ 1 réponse acceptée |
| `resolveur` | Résolveur | ≥ 10 réponses acceptées |
| `entraide` | Entraide | ≥ 25 votes utiles reçus sur des réponses |
| `auteur` | Auteur de tutoriel | ≥ 1 article publié |
| `equipier` | Équipier | ≥ 5 tâches terminées |
| `realisateur` | Réalisateur | ≥ 1 projet terminé |
| `recommande` | Recommandé | ≥ 3 recommandations reçues |
| `mentor` | Mentor | ≥ 1 mentorat terminé |

Les seuils sont administrables (Django Admin → Badges) ; la liste publique est servie par
`GET /api/v1/achievements/`.

## Mise à jour

Les signaux Django (votes, réponses, publications, tâches, projets, recommandations)
resynchronisent les membres concernés **après validation de la transaction**. Le calcul étant
déterministe, rejouer `recompute_reputation` ne change rien si tout est à jour.

## API

- `GET /api/v1/profiles/{username}/reputation/` : score, détail par type, badges (profils
  publics ; un profil privé n'est visible que de son titulaire et de la modération).
- `GET|POST /api/v1/profiles/{username}/recommendations/`, `DELETE /api/v1/recommendations/{id}/`.
- `GET /api/v1/me/dashboard/` : synthèse personnelle (score, contributions, tâches, demandes).
