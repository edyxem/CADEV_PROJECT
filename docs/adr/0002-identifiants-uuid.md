# ADR 0002 — Identifiants UUID pour les ressources exposées

- **Statut :** accepté
- **Date :** 2026-11-13
- **Exigences liées :** §7 (« UUID ou BIGINT »), §10.3 (IDOR)

## Contexte

Le modèle de données laisse le choix entre UUID et entier auto-incrémenté. Les identifiants
figurent dans les URL de l'API (`/posts/{id}/`, `/tasks/{id}/`, `/join-requests/{id}/`…).

## Décision

Toutes les ressources exposées par l'API héritent de `common.models.BaseModel` :

- `id` : `UUIDField` (UUID v4) généré côté application ;
- `created_at` (indexé) et `updated_at`.

Le modèle `User` suit la même règle. Les référentiels publics (catégories, technologies, tags,
pays) et les projets sont en plus adressables par un `slug` ou un code lisible.

## Conséquences

- Impossible d'énumérer les ressources ou d'estimer le volume de la plateforme à partir d'un
  identifiant.
- L'UUID **ne remplace pas** le contrôle d'accès : chaque vue vérifie les permissions et filtre
  son queryset selon la visibilité ; des tests IDOR couvrent les ressources privées.
- Les index sont un peu plus volumineux qu'avec des entiers, ce qui est sans effet à l'échelle
  visée par le MVP.
