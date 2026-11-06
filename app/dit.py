"""Drzewo katalogu (DIT) do podglądu na stronie /directory.

Drzewo budujemy z tych samych wpisów, które obsługuje serwer, więc strona
zawsze pokazuje aktualny stan pliku data/seed.ldif. Pokazujemy tylko
strukturę (RDN, klasę obiektu i krótki opis), a nie wartości atrybutów,
żeby strona nie zdradzała flag ani haseł.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .directory import Entry, normalize_dn
from .ldap_server import ROOT_DN
from .services import ASSETS_DN, PEOPLE_DN

# Wpisy pominięte w podglądzie, bo ich znalezienie jest celem zadania.
# Rekord bez cn i ou z Zadania 3 trzeba odkryć samodzielnie.
HIDDEN_DNS = frozenset({
    normalize_dn("serialNumber=KEY-7731,ou=assets,dc=example,dc=com"),
})

# Które zadanie przeszukuje którą gałąź (base wyszukiwania w services.py).
TASKS_BY_BASE = {
    normalize_dn(ROOT_DN): ("1",),
    normalize_dn(PEOPLE_DN): ("2", "4"),
    normalize_dn(ASSETS_DN): ("3",),
}

# Gdy wpis ma więcej dzieci niż tyle, a wszystkie są liśćmi, układamy je
# w ramce w kilku rzędach (zamiast jednego bardzo szerokiego rzędu).
GROUP_COLUMNS = 4

# Klasy pomocnicze (auxiliary) pomijamy przy wyborze klasy do wyświetlenia.
_AUXILIARY = {"top", "dcobject", "simplesecurityobject"}

# Rodzaj węzła decyduje o kolorze znacznika na stronie.
_KIND_BY_CLASS = {
    "organization": "org",
    "organizationalunit": "ou",
    "inetorgperson": "person",
    "organizationalrole": "role",
    "device": "device",
}


@dataclass
class TreeNode:
    entry: Entry
    children: list[TreeNode] = field(default_factory=list)
    tasks: tuple[str, ...] = ()
    is_root: bool = False

    @property
    def dn(self) -> str:
        return self.entry.dn

    @property
    def rdn(self) -> str:
        return self.entry.dn.split(",", 1)[0].strip()

    @property
    def name(self) -> str:
        """Nazwa na stronie: korzeń ma pełny DN (sufiks), reszta swój RDN."""
        return self.dn if self.is_root else self.rdn

    @property
    def group_children(self) -> bool:
        """Czy dzieci tego wpisu pokazać jako zwartą siatkę liści."""
        return (len(self.children) > GROUP_COLUMNS
                and not any(c.children for c in self.children))

    @property
    def object_class(self) -> str:
        """Najbardziej szczegółowa klasa strukturalna (ostatnia w LDIF)."""
        classes = [c for c in self.entry.get("objectClass")
                   if c.casefold() not in _AUXILIARY]
        return classes[-1] if classes else ""

    @property
    def kind(self) -> str:
        return _KIND_BY_CLASS.get(self.object_class.casefold(), "other")

    @property
    def label(self) -> str | None:
        """Krótki, czytelny opis wpisu (nazwa organizacji, imię i nazwisko...)."""
        rdn_value = self.rdn.split("=", 1)[-1]
        for attr in ("o", "cn"):
            value = self.entry.first(attr)
            if value and value != rdn_value:
                return value
        # Opis bierzemy tylko z urządzeń i ról - u osób bywa w nim flaga.
        if self.kind in ("device", "role"):
            value = self.entry.first("description")
            if value and not value.startswith("FLAG{"):
                return value
        return None


def _parent_dn(dn: str) -> str | None:
    parts = dn.split(",", 1)
    return normalize_dn(parts[1]) if len(parts) == 2 else None


def build_tree(entries: list[Entry]) -> list[TreeNode]:
    """Układa wpisy w drzewo według DN. Zwraca listę korzeni.

    Kolejność dzieci odpowiada kolejności w pliku LDIF.
    """
    nodes: dict[str, TreeNode] = {}
    for entry in entries:
        key = normalize_dn(entry.dn)
        if key in HIDDEN_DNS:
            continue
        nodes[key] = TreeNode(entry, tasks=TASKS_BY_BASE.get(key, ()))

    roots: list[TreeNode] = []
    for key, node in nodes.items():
        parent = nodes.get(_parent_dn(node.dn) or "")
        if parent:
            parent.children.append(node)
        else:
            node.is_root = True
            roots.append(node)
    return roots
