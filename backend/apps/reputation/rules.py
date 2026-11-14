"""Règles de calcul de la réputation, documentées dans ``docs/reputation.md``.

Toute modification ici doit être reportée dans cette documentation.
"""

from dataclasses import dataclass

from .models import EventType


@dataclass(frozen=True)
class Rule:
    points: int
    # Nombre maximal d'événements comptés : par objet (votes) ou au total.
    max_per_object: int | None = None
    max_total: int | None = None


RULES: dict[str, Rule] = {
    EventType.ANSWER_ACCEPTED: Rule(points=15),
    EventType.ANSWER_UPVOTED: Rule(points=2, max_per_object=10),
    EventType.POST_UPVOTED: Rule(points=1, max_per_object=10),
    EventType.ARTICLE_PUBLISHED: Rule(points=5, max_total=20),
    EventType.TASK_COMPLETED: Rule(points=3, max_total=100),
    EventType.PROJECT_COMPLETED: Rule(points=20),
    EventType.RECOMMENDATION_RECEIVED: Rule(points=5, max_total=20),
    EventType.MENTORSHIP_COMPLETED: Rule(points=10, max_total=50),
}

# (code, nom, description, icône, type d'événement, seuil)
DEFAULT_ACHIEVEMENTS = [
    (
        "premiere-solution",
        "Première solution",
        "Une réponse acceptée par l'auteur d'une question.",
        "lightbulb",
        EventType.ANSWER_ACCEPTED,
        1,
    ),
    (
        "resolveur",
        "Résolveur",
        "Dix réponses acceptées.",
        "check-circle",
        EventType.ANSWER_ACCEPTED,
        10,
    ),
    (
        "entraide",
        "Entraide",
        "Vingt-cinq votes utiles reçus sur des réponses.",
        "hands",
        EventType.ANSWER_UPVOTED,
        25,
    ),
    (
        "auteur",
        "Auteur de tutoriel",
        "Un tutoriel ou article publié.",
        "book",
        EventType.ARTICLE_PUBLISHED,
        1,
    ),
    (
        "equipier",
        "Équipier",
        "Cinq tâches de projet terminées.",
        "users",
        EventType.TASK_COMPLETED,
        5,
    ),
    (
        "realisateur",
        "Réalisateur",
        "Membre d'un projet mené à terme.",
        "rocket",
        EventType.PROJECT_COMPLETED,
        1,
    ),
    (
        "recommande",
        "Recommandé",
        "Trois recommandations reçues d'autres membres.",
        "star",
        EventType.RECOMMENDATION_RECEIVED,
        3,
    ),
    ("mentor", "Mentor", "Un mentorat mené à terme.", "compass", EventType.MENTORSHIP_COMPLETED, 1),
]
