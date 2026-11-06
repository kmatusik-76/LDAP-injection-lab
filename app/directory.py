"""Model katalogu LDAP: wpisy (Entry) i wczytywanie danych z pliku LDIF."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Entry:
    """Pojedynczy wpis katalogu.

    Atrybuty trzymamy w kolejnosci wczytania (do czytelnego wyswietlania),
    a wyszukiwanie po nazwie atrybutu jest bez rozroznienia wielkosci liter.
    """

    dn: str
    attributes: list[tuple[str, list[str]]] = field(default_factory=list)
    _index: dict[str, list[str]] = field(default_factory=dict, repr=False)

    def add(self, name: str, value: str) -> None:
        key = name.casefold()
        for i, (existing, values) in enumerate(self.attributes):
            if existing.casefold() == key:
                values.append(value)
                break
        else:
            self.attributes.append((name, [value]))
        self._index.setdefault(key, []).append(value)

    def get(self, name: str) -> list[str]:
        """Zwraca wartosci atrybutu (lista, moze byc pusta)."""
        return self._index.get(name.casefold(), [])

    def first(self, name: str) -> str | None:
        values = self.get(name)
        return values[0] if values else None


def load_ldif(path: Path) -> list[Entry]:
    """Minimalny, ale poprawny parser LDIF dla naszych danych.

    Obsluguje: komentarze (#), puste linie jako separator wpisow, zawijanie
    linii (kontynuacja zaczyna sie od spacji) oraz wartosci base64 zapisane
    jako 'atrybut:: <base64>'.
    """
    entries: list[Entry] = []
    current: Entry | None = None

    def flush():
        nonlocal current
        if current is not None:
            entries.append(current)
        current = None

    # Najpierw sklej zawijane linie w logiczne.
    logical: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(" ") and logical:
            logical[-1] += line[1:]
        else:
            logical.append(line)

    for line in logical:
        if line.startswith("#"):
            continue
        if line.strip() == "":
            flush()
            continue
        if "::" in line and line.split("::", 1)[0].strip().isalnum():
            name, b64 = line.split("::", 1)
            value = base64.b64decode(b64.strip()).decode("utf-8")
        else:
            name, value = line.split(":", 1)
            value = value.lstrip()
        name = name.strip()
        if name == "dn":
            flush()
            current = Entry(dn=value)
        elif current is not None:
            current.add(name, value)

    flush()
    return entries
