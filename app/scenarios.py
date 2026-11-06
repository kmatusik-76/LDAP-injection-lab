"""Opisy zadan (scenariuszy) laboratorium.

Trzymane w jednym miejscu, zeby interfejs, README i testy mowily jednym glosem.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str
    endpoint: str      # nazwa trasy Flaska
    title: str
    goal: str
    time: str
    difficulty: str
    hint: str
    flag: str


SCENARIOS: list[Scenario] = [
    Scenario(
        id="1",
        endpoint="main.login",
        title="Zadanie 1: ominiecie logowania",
        goal="Zaloguj sie jako uzytkownik 'admin', nie znajac jego hasla. "
             "Po zalogowaniu zobaczysz flage w atrybucie description tego konta.",
        time="okolo 10 min",
        difficulty="latwe",
        hint="Haslo trafia do filtra bez zadnej obrobki. Zastanow sie, co "
             "oznacza warunek (userPassword=*) i jak go uzyskac z pola hasla.",
        flag="FLAG{ldap_login_bypass_wildcard}",
    ),
    Scenario(
        id="2",
        endpoint="main.people",
        title="Zadanie 2: wyciek calej ksiazki adresowej",
        goal="Wyswietl pracownikow oznaczonych jako niepubliczni (restricted), "
             "ktorych zwykle wyszukiwanie ukrywa. Flaga jest w polu description "
             "jednego z nich.",
        time="okolo 10 min",
        difficulty="latwe",
        hint="Wpisywana fraza trafia do filtra wprost. Jeden znak potrafi "
             "dopasowac wszystkie wpisy naraz.",
        flag="FLAG{ldap_wildcard_directory_dump}",
    ),
    Scenario(
        id="3",
        endpoint="main.assets",
        title="Zadanie 3: wstrzykniecie warunku OR",
        goal="W katalogu zasobow ukryto rekord bez nazwy (cn) i bez dzialu (ou), "
             "wiec zwykle szukanie go nie znajdzie. Odczytaj flage z jego pola "
             "description.",
        time="okolo 15 min",
        difficulty="srednie",
        hint="Wyszukiwarka sklada filtr (|(cn=...)(ou=...)). Zamknij nawias "
             "wartosci i dodaj wlasny warunek, np. na atrybut description albo "
             "serialNumber. Nowy warunek musi zmiescic sie wewnatrz istniejacego OR.",
        flag="FLAG{ldap_or_attribute_injection}",
    ),
    Scenario(
        id="4",
        endpoint="main.recovery",
        title="Zadanie 4: odczyt na slepo (blind)",
        goal="Formularz odzyskiwania konta mowi tylko, czy konto o podanym "
             "PIN-ie istnieje. Odtworz 4-cyfrowy PIN konta 'aczarnecki', a potem "
             "wpisz go dokladnie, aby odkryc flage.",
        time="okolo 15 min",
        difficulty="trudne",
        hint="PIN trafia do filtra bez obrobki, wiec dziala dopasowanie "
             "fragmentu. Sprawdzaj kolejne cyfry prefiksem, np. '7*', potem "
             "'74*'. Gdy znasz caly PIN, wpisz go bez gwiazdki.",
        flag="FLAG{ldap_blind_pin_extraction}",
    ),
]

SCENARIOS_BY_ENDPOINT: dict[str, Scenario] = {s.endpoint: s for s in SCENARIOS}
ALL_FLAGS: dict[str, str] = {s.flag: s.title for s in SCENARIOS}
