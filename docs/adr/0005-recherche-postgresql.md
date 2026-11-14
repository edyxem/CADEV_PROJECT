# ADR 0005 — Recherche avec PostgreSQL (plein texte + trigrammes)

- **Statut :** accepté
- **Date :** 2026-11-14
- **Exigences liées :** P0-08, module F, §F.4

## Contexte

Le MVP doit permettre de retrouver publications, développeurs et projets par mots-clés, avec des
filtres, sans moteur externe (§F.4). Les contenus sont en français : accents et formes
fléchies (« déploiement » / « deploiements ») doivent être tolérés.

## Décision

- **Configuration `fr_unaccent`** (migration `search.0001`) : copie de la configuration
  `french` avec le dictionnaire `unaccent` placé avant le stemmer français.
- **Publications :** champ `search_vector` (`SearchVectorField`, index GIN) recalculé par le
  service à chaque création ou modification. Poids : titre `A`, contenu `B`, environnement `C`.
  Les balises HTML ne sont pas indexées (le parseur PostgreSQL les ignore).
- **Requête :** `websearch_to_tsquery` (guillemets, `-exclusion` acceptés) **ou** similarité
  trigramme de mots sur le titre (`word_similarity ≥ 0.5`, index GIN `gin_trgm_ops`) pour
  absorber les fautes de frappe.
- **Classement :** `max(rang plein texte, 0,5 × similarité du titre)`, puis date de
  publication. Pas de prise en compte de la popularité : la recherche reste explicable.
- **Profils :** similarité trigramme sur nom d'utilisateur et nom d'affichage, plus
  `unaccent + icontains` sur titre et biographie. Les filtres de l'annuaire s'appliquent.
- **Visibilité :** chaque recherche part d'un sélecteur public (`feed`, `public_profiles`,
  projets publics). Un contenu masqué, supprimé, un brouillon ou un profil privé n'est jamais
  renvoyé.
- **Protection :** endpoints publics, limités par le périmètre `search` (60 requêtes / minute
  par défaut), requête tronquée à 200 caractères.

## Conséquences

- Aucune infrastructure supplémentaire ; la recherche suit les transactions de la base.
- `python manage.py rebuild_search_index` reconstruit l'index après un import massif ou un
  changement de configuration.
- Au-delà de quelques centaines de milliers de documents ou pour un besoin multilingue avancé,
  un moteur dédié pourra être envisagé (P3).
