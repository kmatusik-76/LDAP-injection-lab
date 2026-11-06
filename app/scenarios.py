"""Opisy zadań (scenariuszy) laboratorium.

Trzymane w jednym miejscu, żeby interfejs i testy mówiły jednym głosem.
Fragmenty w `odwrotnych apostrofach` są w interfejsie wyświetlane jako kod.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str
    endpoint: str           # nazwa trasy Flaska
    nav_label: str          # krótka nazwa ekranu w menu
    title: str
    difficulty: str
    time: str
    goal: str               # co trzeba zrobić
    proof: str              # po czym poznać, że się udało
    vulnerability: str      # na czym polega luka
    hints: tuple[str, ...]  # podpowiedzi odsłaniane po kolei
    secure_note: str        # co zmienia tryb BEZPIECZNY
    flag: str


SCENARIOS: list[Scenario] = [
    Scenario(
        id="1",
        endpoint="main.login",
        nav_label="Zadanie 1: logowanie",
        title="Zadanie 1: obejście logowania",
        difficulty="łatwe",
        time="około 10 min",
        goal="Zaloguj się na konto `admin`, nie znając jego hasła.",
        proof="Po zalogowaniu zobaczysz dane konta administratora, a w polu "
              "`description` jego flagę.",
        vulnerability="Aplikacja buduje filtr przez zwykłe sklejenie napisów: "
                      "`(&(uid=TWÓJ_LOGIN)(userPassword=TWOJE_HASŁO))`. Oba pola "
                      "trafiają do niego w takiej postaci, w jakiej je wpiszesz.",
        hints=(
            "Zastanów się, który warunek sprawdza samo istnienie atrybutu, bez "
            "porównywania wartości, i jak zapisać go w polu hasła.",
        ),
        secure_note="Hasło nie trafia już do filtra. Login jest escapowany, "
                    "a hasło sprawdza osobna operacja `bind`, więc gwiazdka "
                    "w polu hasła nic nie daje.",
        flag="FLAG{ldap_login_bypass_wildcard}",
    ),
    Scenario(
        id="2",
        endpoint="main.people",
        nav_label="Zadanie 2: pracownicy",
        title="Zadanie 2: wyciek książki adresowej",
        difficulty="łatwe",
        time="około 10 min",
        goal="Wyświetl pracowników oznaczonych jako niepubliczni (`restricted`), "
             "których wyszukiwarka normalnie ukrywa. Są wśród nich osoby "
             "z zarządu i z działu bezpieczeństwa.",
        proof="W wynikach pojawi się konto z flagą w polu `description`, a razem "
              "z nim prywatne numery telefonów, których nie powinno tam być.",
        vulnerability="Wyszukiwarka skleja filtr "
                      "`(|(cn=FRAZA)(mail=FRAZA)(uid=FRAZA))`, nie ograniczając "
                      "wyników do kont publicznych, a wpisana fraza trafia do "
                      "niego bez obróbki.",
        hints=(
            "Wystarczy jeden znak, żeby warunek pasował do każdego wpisu naraz.",
        ),
        secure_note="Fraza jest escapowana (gwiazdka zamienia się na `\\2a`), "
                    "a filtr ogranicza wyniki do kont `public`. Rekordy "
                    "`restricted` znikają z wyników.",
        flag="FLAG{ldap_wildcard_directory_dump}",
    ),
    Scenario(
        id="3",
        endpoint="main.assets",
        nav_label="Zadanie 3: zasoby",
        title="Zadanie 3: wstrzyknięcie własnego warunku",
        difficulty="średnie",
        time="około 15 min",
        goal="W katalogu zasobów jest rekord, który nie ma ani nazwy (`cn`), ani "
             "działu (`ou`), więc zwykłe wyszukiwanie nigdy go nie zwróci. "
             "Odczytaj flagę z jego pola `description`.",
        proof="W wynikach pojawi się zasób z flagą, choć nie podałeś jego nazwy.",
        vulnerability="Wyszukiwarka skleja filtr `(|(cn=FRAZA)(ou=FRAZA))`. Skoro "
                      "ukryty rekord nie ma `cn` ani `ou`, sama gwiazdka go nie "
                      "znajdzie.",
        hints=(
            "Zamknij nawias wartości i dopisz własny warunek na inny atrybut, na "
            "przykład `description` albo `serialNumber`. Musi się on zmieścić "
            "wewnątrz istniejącego nawiasu `OR`, inaczej serwer odrzuci całe "
            "zapytanie.",
            "Spróbuj wpisać w pole wyszukiwania coś w rodzaju `x)(description=*`. "
            "Zanim zgadniesz, dlaczego to działa, obejrzyj, jak zmienił się filtr.",
        ),
        secure_note="Escapowanie zamyka drogę do wstrzyknięcia nawiasu, "
                    "a dodatkowy warunek `objectClass=device` trzyma wyniki "
                    "w ryzach.",
        flag="FLAG{ldap_or_attribute_injection}",
    ),
    Scenario(
        id="4",
        endpoint="main.recovery",
        nav_label="Zadanie 4: odzyskiwanie",
        title="Zadanie 4: odczyt na ślepo (blind)",
        difficulty="trudne",
        time="około 15 min",
        goal="Formularz odzyskiwania konta zdradza tylko tyle, czy konto "
             "o podanym PIN-ie istnieje, i nie pokazuje żadnych danych. Odtwórz "
             "czterocyfrowy PIN konta `aczarnecki`, a następnie wpisz go "
             "w całości, żeby odsłonić flagę.",
        proof="Po wpisaniu pełnego, poprawnego PIN-u zobaczysz flagę w danych konta.",
        vulnerability="Filtr ma postać `(&(uid=LOGIN)(recoveryPin=PIN))`, a PIN "
                      "trafia do niego bez obróbki, więc działa dopasowanie "
                      "fragmentu. To tak zwany odczyt na ślepo (blind): serwer "
                      "zdradza tajną wartość pojedynczymi odpowiedziami "
                      "„tak/nie”, choć nigdy jej nie wyświetla.",
        hints=(
            "Sprawdzaj PIN prefiksem: wpisuj `0*`, `1*`, `2*`... aż formularz "
            "potwierdzi, że konto istnieje. Tak poznasz pierwszą cyfrę.",
            "Potem dokładaj kolejne. Jeśli pierwsza cyfra to na przykład 5, "
            "sprawdzaj `50*`, `51*`, `52*`... Gdy znasz cały PIN, wpisz go "
            "bez gwiazdki.",
        ),
        secure_note="Escapowanie blokuje dopasowanie prefiksem, a odpowiedź jest "
                    "zawsze taka sama i ogólna. Przy atakach na ślepo samo "
                    "escapowanie to jednak za mało: potrzebne są też ogólne "
                    "komunikaty i ograniczenie liczby prób.",
        flag="FLAG{ldap_blind_pin_extraction}",
    ),
]

SCENARIOS_BY_ENDPOINT: dict[str, Scenario] = {s.endpoint: s for s in SCENARIOS}
ALL_FLAGS: dict[str, str] = {s.flag: s.title for s in SCENARIOS}
