"""Opisy zadań (scenariuszy) laboratorium.

Trzymane w jednym miejscu, żeby interfejs, ZADANIA.md i testy mówiły jednym
głosem.
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
        title="Zadanie 1: obejście logowania",
        goal="Zaloguj się na konto 'admin', nie znając jego hasła. Jeśli się "
             "uda, zobaczysz dane tego konta, a w polu description jego flagę.",
        time="około 10 min",
        difficulty="łatwe",
        hint="Hasło trafia do filtra dokładnie w takiej postaci, w jakiej je "
             "wpiszesz. Pomyśl, który warunek sprawdza samo istnienie atrybutu, "
             "i wstaw go w pole hasła.",
        flag="FLAG{ldap_login_bypass_wildcard}",
    ),
    Scenario(
        id="2",
        endpoint="main.people",
        title="Zadanie 2: wyciek książki adresowej",
        goal="Wyszukiwarka pracowników ma pokazywać tylko konta publiczne. "
             "Wyciągnij z niej również te oznaczone jako 'restricted' - jedno "
             "z nich ma flagę w polu description.",
        time="około 10 min",
        difficulty="łatwe",
        hint="Wpisana fraza wchodzi do filtra bez żadnej obróbki. Wystarczy "
             "jeden znak, żeby warunek pasował do każdego wpisu naraz.",
        flag="FLAG{ldap_wildcard_directory_dump}",
    ),
    Scenario(
        id="3",
        endpoint="main.assets",
        title="Zadanie 3: wstrzyknięcie własnego warunku",
        goal="W katalogu zasobów jest rekord bez nazwy (cn) i bez działu (ou), "
             "więc zwykłe wyszukiwanie nigdy go nie zwróci. Dopisz do filtra "
             "własny warunek i odczytaj flagę z jego pola description.",
        time="około 15 min",
        difficulty="średnie",
        hint="Wyszukiwarka skleja filtr (|(cn=...)(ou=...)). Zamknij nawias "
             "wartości i dodaj warunek na inny atrybut, na przykład description "
             "albo serialNumber. Musi się on zmieścić wewnątrz istniejącego OR, "
             "inaczej serwer odrzuci całe zapytanie.",
        flag="FLAG{ldap_or_attribute_injection}",
    ),
    Scenario(
        id="4",
        endpoint="main.recovery",
        title="Zadanie 4: odczyt na ślepo (blind)",
        goal="Formularz odzyskiwania konta mówi tylko tyle, czy konto o podanym "
             "PIN-ie istnieje. Odtwórz czterocyfrowy PIN konta 'aczarnecki', "
             "a potem wpisz go w całości, żeby odsłonić flagę.",
        time="około 15 min",
        difficulty="trudne",
        hint="PIN trafia do filtra bez obróbki, więc da się dopasować sam "
             "prefiks. Sprawdzaj kolejne cyfry: najpierw '0*', '1*', ... potem "
             "'7*', '74*', '742*'. Gdy znasz cały PIN, wpisz go bez gwiazdki.",
        flag="FLAG{ldap_blind_pin_extraction}",
    ),
]

SCENARIOS_BY_ENDPOINT: dict[str, Scenario] = {s.endpoint: s for s in SCENARIOS}
ALL_FLAGS: dict[str, str] = {s.flag: s.title for s in SCENARIOS}
