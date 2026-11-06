"""Opisy zadań (scenariuszy) laboratorium.

Trzymane w jednym miejscu, żeby interfejs i testy mówiły jednym głosem.
Fragmenty w `odwrotnych apostrofach` są w interfejsie wyświetlane jako kod.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str
    endpoint: str           
    nav_label: str          
    title: str
    difficulty: str
    goal: str              
    proof: str             
    vulnerability: str      
    hints: tuple[str, ...]  
    secure_note: str       
    flag: str


SCENARIOS: list[Scenario] = [
    Scenario(
        id="1",
        endpoint="main.login",
        nav_label="Zadanie 1: logowanie",
        title="Zadanie 1: obejście logowania",
        difficulty="łatwe",
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
                    "a hasło sprawdza osobna operacja `bind`.",
        flag="FLAG{ldap_login_bypass_wildcard}",
    ),
    Scenario(
        id="2",
        endpoint="main.people",
        nav_label="Zadanie 2: pracownicy",
        title="Zadanie 2: wyciek książki adresowej",
        difficulty="łatwe",
        goal="Wyświetl pracowników oznaczonych jako niepubliczni (`restricted`), "
             "których wyszukiwarka normalnie ukrywa. Są wśród nich osoby "
             "z zarządu i z działu bezpieczeństwa.",
        proof="W wynikach pojawi się konto z flagą w polu `description`, a razem "
              "z nim prywatne numery telefonów, których nie powinieneś móc zobaczyć.",
        vulnerability="Wyszukiwarka skleja filtr "
                      "`(|(cn=FRAZA)(mail=FRAZA)(uid=FRAZA))`, nie ograniczając "
                      "wyników do kont publicznych, a wpisana fraza trafia do "
                      "niego bez obróbki.",
        hints=(
            "Chcemy znaleźć dopasowanie do wszystkich wpisów",
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
        goal="W katalogu zasobów jest ukryty rekord z flagą. Nie ma on nazwy "
             "(`cn`) ani działu (`ou`), więc wpisanie (`*`) w wyszukiwarkę "
             "go nie znajdzie. Twoim zadaniem jest tak zmanipulować zapytanie, "
             "żeby wyszukiwarka zwróciła ten rekord.",
        proof="W wynikach pojawi się zasób z flagą, choć nie podałeś jego nazwy.",
        vulnerability="Wyszukiwarka skleja filtr `(|(cn=FRAZA)(ou=FRAZA))` używając wpisanej frazy "
                      "w takiej postaci, w jakiej ją podasz. ",
        hints=(
            "Twój tekst trafia w miejsce `FRAZA` w `(cn=FRAZA)`. Zastanów się, co "
            "się stanie, jeśli w środku wpiszesz `)`, czyli domkniesz warunek `cn` "
            "wcześniej, niż chciał programista.",
        ),
        secure_note="Escapowanie zamyka drogę do wstrzyknięcia nawiasu, "
                    "a dodatkowy warunek `objectClass=device` ogranicza wyniki tylko  do "
                    "tej klasy.",
        flag="FLAG{ldap_or_attribute_injection}",
    ),
    Scenario(
        id="4",
        endpoint="main.recovery",
        nav_label="Zadanie 4: odzyskiwanie",
        title="Zadanie 4: odczyt na ślepo (blind)",
        difficulty="trudne",
        goal="Formularz odzyskiwania konta mówi tylko „konto istnieje” albo "
             "„nie istnieje” - nigdy nie pokazuje PIN-u. Mimo to da się ten "
             "4-cyfrowy PIN konta `aczarnecki` odgadnąć cyfra po cyfrze. "
             "Gdy już go znasz, wpisz go w całości, żeby znaleźć flagę.",
        proof="Po wpisaniu pełnego, poprawnego PIN-u zobaczysz flagę w danych konta.",
        vulnerability="Filtr to `(&(uid=LOGIN)(recoveryPin=PIN))`, a PIN trafia "
                      "do niego bez obróbki, więc gwiazdka działa jak dopasowanie.",
        hints=(
            "Sprawdzaj PIN prefiksem: wpisuj `0*`, `1*`, `2*`... aż formularz "
            "potwierdzi, że konto istnieje. Tak poznasz pierwszą cyfrę.",
            "Potem dokładaj kolejne. Jeśli pierwsza cyfra to na przykład 5, "
            "sprawdzaj `50*`, `51*`, `52*`... Gdy znasz cały PIN, wpisz go "
            "bez gwiazdki.",
        ),
        secure_note="Escapowanie blokuje dopasowanie prefiksem, a odpowiedź jest "
                    "zawsze taka sama i ogólna.",
        flag="FLAG{ldap_blind_pin_extraction}",
    ),
]

SCENARIOS_BY_ENDPOINT: dict[str, Scenario] = {s.endpoint: s for s in SCENARIOS}
SCENARIOS_BY_FLAG: dict[str, Scenario] = {s.flag: s for s in SCENARIOS}
