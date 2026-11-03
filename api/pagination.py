"""Paginación para los GET de listado (convención cantidad → paginación → todos → filtros).

Dos helpers según viva la lista:

- ``pagina_limit_offset`` → SQL: devuelve la cláusula y sus parámetros.
- ``paginar_lista``       → listas ya materializadas en memoria.

En ambos casos los defaults del repo (``limit=None``, ``skip=0``, ``todos=False``)
reproducen el comportamiento previo a existir la paginación: sin ``LIMIT``.
"""
from __future__ import annotations

from typing import Any, Sequence, TypeVar

T = TypeVar("T")


def pagina_limit_offset(limit: int | None, skip: int = 0, todos: bool = False) -> tuple[str, dict[str, Any]]:
    """Cláusula SQL de paginación + parámetros a inyectar en la query.

    - ``todos=True``   → sin ``LIMIT``/``OFFSET``.
    - ``limit=None``   → sin ``LIMIT``; ``skip`` sólo genera ``OFFSET`` si > 0.
    - ``limit=<n>``    → ``LIMIT :limit OFFSET :skip``.

    Los parámetros devueltos deben fusionarse en los de la query: sólo se envían
    los que la cláusula realmente usa (SQLAlchemy rechaza bind params sin usar).
    """
    if todos:
        return "", {}
    if limit is None:
        if skip:
            return " OFFSET :skip", {"skip": skip}
        return "", {}
    return " LIMIT :limit OFFSET :skip", {"limit": limit, "skip": skip}


def paginar_lista(items: Sequence[T], limit: int | None = None,
                  skip: int = 0, todos: bool = False) -> list[T]:
    """Paginación en memoria para listas ya calculadas (reportes, agrupaciones…).

    Con los defaults (``limit=None``, ``skip=0``, ``todos=False``) devuelve la
    lista entera, idéntico a no paginar.
    """
    if todos:
        return list(items)
    start = skip or 0
    if limit is None:
        return list(items[start:])
    return list(items[start:start + limit])
