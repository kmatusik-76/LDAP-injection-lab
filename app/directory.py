"""Model katalogu LDAP: wpisy (Entry) i wczytywanie danych z pliku LDIF."""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass, field
from pathlib import Path


class LdifError(ValueError):
    """Plik LDIF jest niepoprawny - komunikat wskazuje numer linii."""


@dataclass
class Entry:
    """Pojedynczy wpis katalogu.

    Atrybuty trzymamy w kolejności wczytania (do czytelnego wyświetlania),
    a wyszukiwanie po nazwie atrybutu jest bez rozróżnienia wielkości liter.
    """

    dn: str
    attributes: list[tuple[str, list[str]]] = field(default_factory=list)
    _index: dict[str, list[str]] = field(default_factory=dict, repr=False)

    def add(self, name: str, value: str) -> None:
        key = name.casefold()
        for existing, values in self.attributes:
            if existing.casefold() == key:
                values.append(value)
                break
        else:
            self.attributes.append((name, [value]))
        self._index.setdefault(key, []).append(value)

    def get(self, name: str) -> list[str]:
        """Zwraca wartości atrybutu (lista, może być pusta)."""
        return self._index.get(name.casefold(), [])

    def first(self, name: str) -> str | None:
        values = self.get(name)
        return values[0] if values else None


def normalize_dn(dn: str) -> str:
    """Normalizuje DN do porównań: małe litery, bez spacji wokół przecinków."""
    return ",".join(part.strip() for part in dn.casefold().split(","))


# Linia LDIF to "nazwa: wartość" albo "nazwa:: wartość-w-base64".
_LDIF_LINE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)(::|:)(.*)$")


def load_ldif(path: Path) -> list[Entry]:
    """Minimalny, ale poprawny parser LDIF dla naszych danych.

    Obsługuje: komentarze (#), puste linie jako separator wpisów, zawijanie
    linii (kontynuacja zaczyna się od spacji) oraz wartości base64 zapisane
    jako 'atrybut:: <base64>'.
    """
    entries: list[Entry] = []
    current: Entry | None = None

    def flush() -> None:
        nonlocal current
        if current is not None:
            entries.append(current)
        current = None

    # Najpierw sklej zawijane linie w logiczne, pamiętając numer linii z pliku
    # (przyda się w komunikacie o błędzie).
    logical: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith(" ") and logical:
            prev_no, prev_text = logical[-1]
            logical[-1] = (prev_no, prev_text + line[1:])
        else:
            logical.append((lineno, line))

    for lineno, line in logical:
        if line.startswith("#"):
            continue
        if not line.strip():
            flush()
            continue

        match = _LDIF_LINE.match(line)
        if match is None:
            raise LdifError(
                f"{path.name}, linia {lineno}: oczekiwano 'atrybut: wartość', "
                f"a jest: {line!r}"
            )
        name, separator, raw = match.group(1), match.group(2), match.group(3)
        if separator == "::":
            try:
                value = base64.b64decode(raw.strip(), validate=True).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError) as exc:
                raise LdifError(
                    f"{path.name}, linia {lineno}: nieprawidłowa wartość base64 "
                    f"atrybutu '{name}': {exc}"
                ) from exc
        else:
            value = raw.lstrip()

        if name.casefold() == "dn":
            flush()
            current = Entry(dn=value)
        elif current is None:
            raise LdifError(
                f"{path.name}, linia {lineno}: atrybut '{name}' pojawił się "
                "przed pierwszą linią 'dn:'."
            )
        else:
            current.add(name, value)

    flush()
    return entries
