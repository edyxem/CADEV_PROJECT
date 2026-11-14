"""Paramètres partagés de la recherche plein texte PostgreSQL."""

# Configuration créée par la migration ``search.0001`` : français + suppression des accents,
# pour que « securite » trouve « sécurité ».
SEARCH_CONFIG = "fr_unaccent"
