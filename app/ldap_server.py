"""Zmockowany serwer LDAP dzialajacy w pamieci.

Serwer wykonuje dwie operacje, tak jak prawdziwy katalog:

  * search(base, filtr, scope) - zwraca wpisy pasujace do filtra,
  * bind(dn, haslo)           - sprawdza poswiadczenia konkretnego wpisu.

Serwer nie wie nic o "atakach" ani "trybach bezpiecznych". Cala logika budowania
filtra (i ewentualne podatnosci) zyje warstwe wyzej, w app/services.py.
"""

from __future__ import annotations

from pathlib import Path

from .directory import Entry, load_ldif
from .ldap_filter import parse_filter

# Zasiegi wyszukiwania (jak w LDAP).
BASE = "base"          # tylko wpis wskazany przez base
ONELEVEL = "onelevel"  # bezposrednie dzieci base
SUBTREE = "subtree"    # base i wszystko ponizej

ROOT_DN = "dc=example,dc=com"

_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed.ldif"


def _norm_dn(dn: str) -> str:
    """Normalizuje DN do porownan: male litery, bez spacji wokol przecinkow."""
    return ",".join(part.strip() for part in dn.casefold().split(","))


def _in_scope(entry_dn: str, base: str, scope: str) -> bool:
    e = _norm_dn(entry_dn)
    b = _norm_dn(base)
    if scope == BASE:
        return e == b
    if scope == ONELEVEL:
        return e.endswith("," + b) and e.count(",") == b.count(",") + 1
    # SUBTREE
    return e == b or e.endswith("," + b)


class MockLdapServer:
    def __init__(self, seed_path: Path | None = None):
        self.entries: list[Entry] = load_ldif(seed_path or _SEED_PATH)
        self._by_dn: dict[str, Entry] = {_norm_dn(e.dn): e for e in self.entries}

    def search(self, base: str, ldap_filter: str, scope: str = SUBTREE) -> list[Entry]:
        """Zwraca wpisy w zasiegu base, ktore pasuja do filtra.

        Rzuca FilterError (z ldap_filter), gdy filtr jest skladniowo bledny -
        tak jak serwer odrzucilby niepoprawne zapytanie.
        """
        node = parse_filter(ldap_filter)
        return [
            e
            for e in self.entries
            if _in_scope(e.dn, base, scope) and node.matches(e)
        ]

    def bind(self, dn: str, password: str) -> bool:
        """Sprawdza haslo wpisu (porownanie userPassword, z rozroznieniem liter)."""
        entry = self._by_dn.get(_norm_dn(dn))
        if entry is None or not password:
            return False
        return password in entry.get("userPassword")
