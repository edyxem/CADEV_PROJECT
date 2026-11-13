"""Contrôle des transitions de statut à partir d'une table explicite."""

from collections.abc import Collection, Mapping

from common.exceptions import InvalidTransition

TransitionTable = Mapping[str, Collection[str]]


def can_transition(table: TransitionTable, current: str, target: str) -> bool:
    """Indique si ``current -> target`` figure dans la table."""
    return target in table.get(current, ())


def ensure_transition(table: TransitionTable, current: str, target: str) -> None:
    """Lève ``InvalidTransition`` si le changement de statut est interdit."""
    if not can_transition(table, current, target):
        raise InvalidTransition(f"Transition interdite : {current} → {target}.")
