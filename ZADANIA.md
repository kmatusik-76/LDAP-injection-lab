# Zadania

Aplikacja startuje w trybie **PODATNY** (czerwony pasek u góry). W tym trybie
wykonaj zadania i zdobądź flagi. Następnie przełącz na **BEZPIECZNY** (zielony
pasek) i sprawdź, że te same ataki już nie działają — to jest właśnie sedno
całego ćwiczenia.

Pod każdym formularzem widać **filtr LDAP wysłany do serwera**, a obok sekcję,
która pokazuje, jak serwer ten filtr rozumie. Zaglądaj tam po każdej próbie —
najlepiej widać wtedy, co dokładnie zmieniło się w zapytaniu. Jeśli chcesz
najpierw oswoić się ze składnią filtrów, otwórz **Konsolę LDAP** i poćwicz na
danych z piaskownicy (tam nie ma flag).

Flagi mają format `FLAG{...}`. Każdą z nich możesz potwierdzić na stronie
**Sprawdź flagę**.

---

## Zadanie 1: obejście logowania

- **Trudność:** łatwe
- **Czas:** około 10 minut
- **Ekran:** Zadanie 1: logowanie

**Cel:** zalogować się na konto `admin`, nie znając jego hasła.

**Dowód wykonania:** po zalogowaniu zobaczysz dane konta administratora,
a w polu `description` jego flagę.

**Na czym polega luka:** aplikacja buduje filtr przez zwykłe sklejenie napisów:
`(&(uid=TWÓJ_LOGIN)(userPassword=TWOJE_HASŁO))`. Oba pola trafiają do niego
w takiej postaci, w jakiej je wpiszesz. Zastanów się, który warunek sprawdza
samo istnienie atrybutu, bez porównywania wartości, i jak zapisać go w polu
hasła.

---

## Zadanie 2: wyciek książki adresowej

- **Trudność:** łatwe
- **Czas:** około 10 minut
- **Ekran:** Zadanie 2: pracownicy

**Cel:** wyświetlić pracowników oznaczonych jako niepubliczni (`restricted`),
których wyszukiwarka normalnie ukrywa. Są wśród nich osoby z zarządu i z działu
bezpieczeństwa.

**Dowód wykonania:** w wynikach pojawi się konto z flagą w polu `description`,
a razem z nim prywatne numery telefonów, których nie powinno tam być.

**Na czym polega luka:** wyszukiwarka skleja filtr
`(|(cn=FRAZA)(mail=FRAZA)(uid=FRAZA))`, nie ograniczając wyników do kont
publicznych, a wpisana fraza trafia do niego bez obróbki. Wystarczy jeden znak,
żeby warunek pasował do każdego wpisu naraz.

---

## Zadanie 3: wstrzyknięcie własnego warunku

- **Trudność:** średnie
- **Czas:** około 15 minut
- **Ekran:** Zadanie 3: zasoby

**Cel:** w katalogu zasobów jest rekord, który nie ma ani nazwy (`cn`), ani
działu (`ou`), więc zwykłe wyszukiwanie nigdy go nie zwróci. Odczytaj flagę
z jego pola `description`.

**Dowód wykonania:** w wynikach pojawi się zasób z flagą, choć nie podałeś jego
nazwy.

**Na czym polega luka:** wyszukiwarka skleja filtr `(|(cn=FRAZA)(ou=FRAZA))`.
Skoro ukryty rekord nie ma `cn` ani `ou`, sama gwiazdka go nie znajdzie. Zamknij
nawias wartości i dopisz własny warunek na inny atrybut, na przykład
`description` albo `serialNumber`. Musi się on zmieścić wewnątrz istniejącego
nawiasu `OR`, inaczej serwer odrzuci całe zapytanie.

Podpowiedź co do składni: spróbuj wpisać w pole wyszukiwania coś w rodzaju
`x)(description=*`. Zanim zgadniesz, dlaczego to działa, obejrzyj w podglądzie,
jak zmienił się filtr.

---

## Zadanie 4: odczyt na ślepo (blind)

- **Trudność:** trudne
- **Czas:** około 15 minut
- **Ekran:** Zadanie 4: odzyskiwanie

**Cel:** formularz odzyskiwania konta zdradza tylko tyle, czy konto o podanym
PIN-ie istnieje — żadnych danych nie pokazuje. Odtwórz czterocyfrowy PIN konta
`aczarnecki`, a następnie wpisz go w całości, żeby odsłonić flagę.

**Dowód wykonania:** po wpisaniu pełnego, poprawnego PIN-u zobaczysz flagę
w danych konta.

**Na czym polega luka:** filtr ma postać `(&(uid=LOGIN)(recoveryPin=PIN))`, a PIN
trafia do niego bez obróbki, więc działa dopasowanie fragmentu. Sprawdzaj kolejne
cyfry prefiksem: wpisuj `0*`, `1*`, ... aż formularz potwierdzi, że konto
istnieje — to daje pierwszą cyfrę. Potem dokładaj następne, na przykład `7*`,
`74*`, `742*`. Gdy znasz cały PIN, wpisz go bez gwiazdki.

Taki atak nazywamy odczytem na ślepo (blind): serwer wydobywa tajną wartość
pojedynczymi odpowiedziami "tak/nie", choć nigdy jej nie wyświetla.

---

## Po wykonaniu: przełącz na BEZPIECZNY

Kliknij **Przełącz na BEZPIECZNY** w górnym pasku i powtórz wszystkie ataki.
Zwróć uwagę, co się zmienia:

- **Zadanie 1:** hasło nie trafia już do filtra. Login jest escapowany, a hasło
  sprawdza osobna operacja `bind`. Gwiazdka w polu hasła nic nie daje.
- **Zadanie 2:** fraza jest escapowana (gwiazdka zamienia się na `\2a`), a filtr
  ogranicza wyniki do kont `public`. Rekordy `restricted` znikają z wyników.
- **Zadanie 3:** escapowanie zamyka drogę do wstrzyknięcia nawiasu, a dodatkowy
  warunek `objectClass=device` trzyma wyniki w ryzach.
- **Zadanie 4:** escapowanie blokuje dopasowanie prefiksem, a odpowiedź jest
  zawsze taka sama i ogólna. Pamiętaj jednak, że przy atakach na ślepo samo
  escapowanie to za mało — potrzebne są też ogólne komunikaty i ograniczenie
  liczby prób.
