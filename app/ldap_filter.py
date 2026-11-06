"""Lekki parser i ewaluator filtrow LDAP (podzbior RFC 4515).

To jest serce laboratorium. Serwer LDAP nie "rozumie" atakow: on po prostu
bierze napis z filtrem, rozklada go na drzewo warunkow i sprawdza, ktore wpisy
mu odpowiadaja. Wstrzykniecie LDAP dziala wlasnie dlatego, ze aplikacja skleja
napis z filtrem z niezaufanych danych uzytkownika, przez co to drzewo wyglada
inaczej, niz zakladal programista.

Obslugiwana skladnia:

    filtr      = "(" tresc ")"
    tresc      = "&" lista | "|" lista | "!" filtr | warunek
    lista      = filtr+
    warunek    = atrybut operator wartosc
    operator   = "=" | ">=" | "<=" | "~="

Wartosc moze zawierac:
    *              znak wieloznaczny (obecnosc / dopasowanie fragmentu),
    \\XX           sekwencje escape (np. \\2a to doslowna gwiazdka).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


class FilterError(ValueError):
    """Blad skladni filtra - odpowiednik odrzucenia zapytania przez serwer."""


# --- Escapowanie wartosci (RFC 4515) ---------------------------------------

# Znaki, ktore w wartosci filtra maja znaczenie specjalne. Bezpieczny kod musi
# zamienic je na sekwencje \\XX, zanim wklei dane uzytkownika do filtra.
_SPECIAL = {
    "*": "\\2a",
    "(": "\\28",
    ")": "\\29",
    "\\": "\\5c",
    "\x00": "\\00",
}


def escape_filter_chars(value: str) -> str:
    """Zamienia znaki specjalne na sekwencje \\XX (jak w bibliotekach LDAP)."""
    return "".join(_SPECIAL.get(ch, ch) for ch in value)


# Marker znaku wieloznacznego (odrozniony od doslownej gwiazdki po escapowaniu).
class _Wildcard:
    def __repr__(self):
        return "*"


WILDCARD = _Wildcard()

_HEX = set("0123456789abcdefABCDEF")


def _tokenize_value(raw: str) -> list:
    """Rozklada surowa wartosc na liste: doslowne znaki i markery WILDCARD.

    Sekwencje \\XX zamienia na doslowny znak (wiec \\2a to zwykla gwiazdka,
    a nie znak wieloznaczny). Niezescapowana gwiazdka staje sie WILDCARD.
    """
    tokens: list = []
    i, n = 0, len(raw)
    while i < n:
        ch = raw[i]
        if ch == "\\":
            hexpart = raw[i + 1 : i + 3]
            if len(hexpart) == 2 and hexpart[0] in _HEX and hexpart[1] in _HEX:
                tokens.append(chr(int(hexpart, 16)))
                i += 3
            else:
                raise FilterError(f"Nieprawidlowa sekwencja escape: '\\{hexpart}'")
        elif ch == "*":
            tokens.append(WILDCARD)
            i += 1
        else:
            tokens.append(ch)
            i += 1
    return tokens


# --- Wezly drzewa filtra ----------------------------------------------------


@dataclass
class And:
    children: list

    def matches(self, entry) -> bool:
        return all(c.matches(entry) for c in self.children)


@dataclass
class Or:
    children: list

    def matches(self, entry) -> bool:
        return any(c.matches(entry) for c in self.children)


@dataclass
class Not:
    child: object

    def matches(self, entry) -> bool:
        return not self.child.matches(entry)


@dataclass
class Present:
    """(atrybut=*) - wpis ma ten atrybut z dowolna wartoscia."""

    attr: str

    def matches(self, entry) -> bool:
        return bool(entry.get(self.attr))


@dataclass
class Equality:
    attr: str
    value: str

    def matches(self, entry) -> bool:
        target = self.value.casefold()
        return any(v.casefold() == target for v in entry.get(self.attr))


@dataclass
class Substring:
    """(atrybut=frag*ment) - dopasowanie fragmentow rozdzielonych gwiazdka."""

    attr: str
    parts: list  # doslowne segmenty; puste na brzegach oznaczaja gwiazdke

    def matches(self, entry) -> bool:
        pattern = "^" + ".*".join(re.escape(p) for p in self.parts) + "$"
        rx = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        return any(rx.match(v) for v in entry.get(self.attr))


@dataclass
class Comparison:
    """(atrybut>=wartosc) i (atrybut<=wartosc) - porownanie."""

    attr: str
    value: str
    op: str  # ">=" lub "<="

    def matches(self, entry) -> bool:
        for v in entry.get(self.attr):
            if _compare(v, self.value, self.op):
                return True
        return False


def _compare(left: str, right: str, op: str) -> bool:
    # Jesli obie strony sa liczbami, porownaj liczbowo; inaczej leksykalnie.
    try:
        a: object = float(left)
        b: object = float(right)
    except ValueError:
        a, b = left.casefold(), right.casefold()
    return a >= b if op == ">=" else a <= b


# --- Parser (zejscie rekurencyjne) ------------------------------------------


class _Parser:
    def __init__(self, text: str):
        self.s = text
        self.i = 0
        self.n = len(text)

    def parse(self):
        node = self._filter()
        if self.i != self.n:
            raise FilterError(
                "Nadmiarowe znaki po zamknieciu filtra - filtr musi byc "
                "pojedynczym, poprawnie domknietym wyrazeniem."
            )
        return node

    def _peek(self) -> str:
        return self.s[self.i] if self.i < self.n else ""

    def _filter(self):
        if self._peek() != "(":
            raise FilterError("Oczekiwano '(' na poczatku filtra.")
        self.i += 1
        node = self._content()
        if self._peek() != ")":
            raise FilterError("Oczekiwano ')' - niedomkniety filtr.")
        self.i += 1
        return node

    def _content(self):
        c = self._peek()
        if c == "&":
            self.i += 1
            return And(self._filter_list())
        if c == "|":
            self.i += 1
            return Or(self._filter_list())
        if c == "!":
            self.i += 1
            return Not(self._filter())
        return self._item()

    def _filter_list(self):
        items = []
        while self._peek() == "(":
            items.append(self._filter())
        if not items:
            raise FilterError("Operator '&' lub '|' wymaga co najmniej jednego warunku.")
        return items

    def _item(self):
        start = self.i
        while self.i < self.n and self.s[self.i] not in "=<>~()":
            self.i += 1
        attr = self.s[start : self.i].strip()
        op_char = self._peek()
        if op_char in "<>~":
            if self.s[self.i + 1 : self.i + 2] != "=":
                raise FilterError(f"Oczekiwano '=' po operatorze '{op_char}'.")
            self.i += 2
            value = self._read_value()
            if not attr:
                raise FilterError("Brak nazwy atrybutu przed operatorem.")
            if op_char == "~":
                return Equality(attr, value)  # przyblizone traktujemy jak rownosc
            return Comparison(attr, value, op_char + "=")
        if op_char == "=":
            self.i += 1
            raw = self._read_value()
            if not attr:
                raise FilterError("Brak nazwy atrybutu przed '='.")
            return _build_match(attr, raw)
        raise FilterError("Niekompletny warunek - brak operatora.")

    def _read_value(self) -> str:
        # Wartosc konczy sie na pierwszym niezescapowanym nawiasie.
        start = self.i
        while self.i < self.n and self.s[self.i] not in "()":
            self.i += 1
        return self.s[start : self.i]


def _build_match(attr: str, raw: str):
    """Z surowej wartosci buduje odpowiedni wezel: rownosc, obecnosc lub fragment."""
    tokens = _tokenize_value(raw)
    if WILDCARD not in tokens:
        return Equality(attr, "".join(tokens))

    # Podziel na segmenty literalow rozdzielone gwiazdkami.
    parts: list[str] = [""]
    for tok in tokens:
        if tok is WILDCARD:
            parts.append("")
        else:
            parts[-1] += tok

    # Sama gwiazdka (parts == ["", ""]) to test obecnosci atrybutu.
    if all(p == "" for p in parts):
        return Present(attr)
    return Substring(attr, parts)


def parse_filter(text: str):
    """Parsuje napis z filtrem LDAP na drzewo warunkow. Rzuca FilterError."""
    if not isinstance(text, str) or not text.strip():
        raise FilterError("Pusty filtr.")
    return _Parser(text.strip()).parse()


# --- Pomocniczy, czytelny opis drzewa (do UI i debugowania) -----------------


def describe(node, indent: int = 0) -> str:
    """Zwraca wcietą, czytelna reprezentacje drzewa filtra."""
    pad = "  " * indent
    if isinstance(node, And):
        head = f"{pad}AND (wszystkie warunki musza byc spelnione)"
        return "\n".join([head] + [describe(c, indent + 1) for c in node.children])
    if isinstance(node, Or):
        head = f"{pad}OR (wystarczy jeden warunek)"
        return "\n".join([head] + [describe(c, indent + 1) for c in node.children])
    if isinstance(node, Not):
        return f"{pad}NOT\n" + describe(node.child, indent + 1)
    if isinstance(node, Present):
        return f"{pad}{node.attr} istnieje (dowolna wartosc)"
    if isinstance(node, Equality):
        return f"{pad}{node.attr} == '{node.value}'"
    if isinstance(node, Substring):
        return f"{pad}{node.attr} pasuje do wzorca '{'*'.join(node.parts)}'"
    if isinstance(node, Comparison):
        return f"{pad}{node.attr} {node.op} '{node.value}'"
    return f"{pad}?"
