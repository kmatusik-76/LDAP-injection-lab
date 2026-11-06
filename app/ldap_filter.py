"""Lekki parser i ewaluator filtrów LDAP (podzbiór RFC 4515).

To jest serce laboratorium. Serwer LDAP nie "rozumie" ataków: on po prostu
bierze napis z filtrem, rozkłada go na drzewo warunków i sprawdza, które wpisy
mu odpowiadają. Wstrzyknięcie LDAP działa właśnie dlatego, że aplikacja skleja
napis z filtrem z niezaufanych danych użytkownika, przez co to drzewo wygląda
inaczej, niż założył programista.

Obsługiwana składnia:

    filtr      = "(" treść ")"
    treść      = "&" lista | "|" lista | "!" filtr | warunek
    lista      = filtr+
    warunek    = atrybut operator wartość
    operator   = "=" | ">=" | "<=" | "~="

Wartość może zawierać:
    *              znak wieloznaczny (obecność / dopasowanie fragmentu),
    \\XX           sekwencje escape (np. \\2a to dosłowna gwiazdka).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Maksymalna głębokość zagnieżdżenia filtra. Prawdziwe serwery też mają taki
#: limit - bez niego wystarczyłby filtr w rodzaju "(&(&(&(&..." , żeby zabić
#: proces przepełnieniem stosu zamiast dostać czytelny błąd składni.
MAX_DEPTH = 64


class FilterError(ValueError):
    """Błąd składni filtra - odpowiednik odrzucenia zapytania przez serwer."""


# --- Escapowanie wartości (RFC 4515) ---------------------------------------

# Znaki, które w wartości filtra mają znaczenie specjalne. Bezpieczny kod musi
# zamienić je na sekwencje \\XX, zanim wklei dane użytkownika do filtra.
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


# Marker znaku wieloznacznego (odróżniony od dosłownej gwiazdki po escapowaniu).
class _Wildcard:
    def __repr__(self):
        return "*"


WILDCARD = _Wildcard()

_HEX = set("0123456789abcdefABCDEF")


def _tokenize_value(raw: str) -> list:
    """Rozkłada surową wartość na listę: dosłowne znaki i markery WILDCARD.

    Sekwencje \\XX zamienia na dosłowny znak (więc \\2a to zwykła gwiazdka,
    a nie znak wieloznaczny). Niezescapowana gwiazdka staje się WILDCARD.
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
                raise FilterError(f"Nieprawidłowa sekwencja escape: '\\{hexpart}'")
        elif ch == "*":
            tokens.append(WILDCARD)
            i += 1
        else:
            tokens.append(ch)
            i += 1
    return tokens


# --- Węzły drzewa filtra ----------------------------------------------------


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
    """(atrybut=*) - wpis ma ten atrybut z dowolną wartością."""

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
    """(atrybut=frag*ment) - dopasowanie fragmentów rozdzielonych gwiazdką."""

    attr: str
    parts: list  # dosłowne segmenty; puste na brzegach oznaczają gwiazdkę

    def __post_init__(self):
        # Wzorzec kompilujemy raz, a nie dla każdego sprawdzanego wpisu.
        pattern = "^" + ".*".join(re.escape(p) for p in self.parts) + "$"
        self._regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)

    def matches(self, entry) -> bool:
        return any(self._regex.match(v) for v in entry.get(self.attr))


@dataclass
class Comparison:
    """(atrybut>=wartość) i (atrybut<=wartość) - porównanie."""

    attr: str
    value: str
    op: str  # ">=" lub "<="

    def matches(self, entry) -> bool:
        return any(_compare(v, self.value, self.op) for v in entry.get(self.attr))


def _compare(left: str, right: str, op: str) -> bool:
    # Jeśli obie strony są liczbami, porównaj liczbowo; inaczej leksykalnie.
    try:
        a: object = float(left)
        b: object = float(right)
    except ValueError:
        a, b = left.casefold(), right.casefold()
    return a >= b if op == ">=" else a <= b


# --- Parser (zejście rekurencyjne) ------------------------------------------


class _Parser:
    def __init__(self, text: str):
        self.s = text
        self.i = 0
        self.n = len(text)
        self.depth = 0

    def parse(self):
        node = self._filter()
        if self.i != self.n:
            raise FilterError(
                "Nadmiarowe znaki po zamknięciu filtra - filtr musi być "
                "pojedynczym, poprawnie domkniętym wyrażeniem."
            )
        return node

    def _peek(self) -> str:
        return self.s[self.i] if self.i < self.n else ""

    def _filter(self):
        if self._peek() != "(":
            raise FilterError("Oczekiwano '(' na początku filtra.")
        if self.depth >= MAX_DEPTH:
            raise FilterError(
                f"Filtr jest zagnieżdżony głębiej niż {MAX_DEPTH} poziomów."
            )
        self.depth += 1
        self.i += 1
        node = self._content()
        if self._peek() != ")":
            raise FilterError("Oczekiwano ')' - niedomknięty filtr.")
        self.i += 1
        self.depth -= 1
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
                return Equality(attr, value)  # przybliżone traktujemy jak równość
            return Comparison(attr, value, op_char + "=")
        if op_char == "=":
            self.i += 1
            raw = self._read_value()
            if not attr:
                raise FilterError("Brak nazwy atrybutu przed '='.")
            return _build_match(attr, raw)
        raise FilterError("Niekompletny warunek - brak operatora.")

    def _read_value(self) -> str:
        # Wartość kończy się na pierwszym niezescapowanym nawiasie.
        start = self.i
        while self.i < self.n and self.s[self.i] not in "()":
            self.i += 1
        return self.s[start : self.i]


def _build_match(attr: str, raw: str):
    """Z surowej wartości buduje odpowiedni węzeł: równość, obecność lub fragment."""
    tokens = _tokenize_value(raw)
    if WILDCARD not in tokens:
        return Equality(attr, "".join(tokens))

    # Podziel na segmenty literałów rozdzielone gwiazdkami.
    parts: list[str] = [""]
    for tok in tokens:
        if tok is WILDCARD:
            parts.append("")
        else:
            parts[-1] += tok

    # Sama gwiazdka (parts == ["", ""]) to test obecności atrybutu.
    if all(p == "" for p in parts):
        return Present(attr)
    return Substring(attr, parts)


def parse_filter(text: str):
    """Parsuje napis z filtrem LDAP na drzewo warunków. Rzuca FilterError."""
    if not isinstance(text, str) or not text.strip():
        raise FilterError("Pusty filtr.")
    return _Parser(text.strip()).parse()


# --- Pomocniczy, czytelny opis drzewa (do UI i debugowania) -----------------


def describe(node, indent: int = 0) -> str:
    """Zwraca wciętą, czytelną reprezentację drzewa filtra."""
    pad = "  " * indent
    if isinstance(node, And):
        head = f"{pad}AND (wszystkie warunki muszą być spełnione)"
        return "\n".join([head] + [describe(c, indent + 1) for c in node.children])
    if isinstance(node, Or):
        head = f"{pad}OR (wystarczy jeden warunek)"
        return "\n".join([head] + [describe(c, indent + 1) for c in node.children])
    if isinstance(node, Not):
        return f"{pad}NOT\n" + describe(node.child, indent + 1)
    if isinstance(node, Present):
        return f"{pad}{node.attr} istnieje (dowolna wartość)"
    if isinstance(node, Equality):
        return f"{pad}{node.attr} == '{node.value}'"
    if isinstance(node, Substring):
        return f"{pad}{node.attr} pasuje do wzorca '{'*'.join(node.parts)}'"
    if isinstance(node, Comparison):
        return f"{pad}{node.attr} {node.op} '{node.value}'"
    return f"{pad}?"
