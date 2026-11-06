# Zadania

Aplikacja startuje w trybie **PODATNY** (czerwony pasek u gory). W tym trybie
wykonaj zadania i zdobadz flagi. Potem przelacz na **BEZPIECZNY** (zielony pasek)
i sprawdz, ze te same ataki juz nie dzialaja. To jest cala lekcja.

Pod kazdym formularzem widac **filtr LDAP wyslany do serwera** oraz sekcje
pokazujaca, jak serwer go rozumie. Obserwuj, jak filtr zmienia sie po wpisaniu
roznych rzeczy. Jesli chcesz najpierw oswoic sie ze skladnia filtrow, otworz
**Konsole LDAP** i poeksperymentuj na danych z piaskownicy (tam nie ma flag).

Flagi maja format `FLAG{...}`. Mozesz je potwierdzic na stronie **Sprawdz flage**.

---

## Zadanie 1: ominiecie logowania

- **Trudnosc:** latwe
- **Czas:** okolo 10 minut
- **Ekran:** Zadanie 1: logowanie

**Cel:** zalogowac sie jako uzytkownik `admin`, nie znajac jego hasla.

**Dowod wykonania:** po zalogowaniu zobaczysz dane konta admina, a w polu
`description` flage.

**Na czym polega luka:** aplikacja buduje filtr tak:
`(&(uid=TWOJ_LOGIN)(userPassword=TWOJE_HASLO))`. Oba pola trafiaja do filtra bez
obrobki. Zastanow sie, co oznacza warunek sprawdzajacy samo istnienie hasla i jak
zapisac go w polu hasla.

---

## Zadanie 2: wyciek calej ksiazki adresowej

- **Trudnosc:** latwe
- **Czas:** okolo 10 minut
- **Ekran:** Zadanie 2: pracownicy

**Cel:** wyswietlic pracownikow oznaczonych jako niepubliczni (`restricted`),
ktorych zwykle wyszukiwanie ukrywa. Sa wsrod nich osoby z zarzadu i z dzialu
bezpieczenstwa.

**Dowod wykonania:** wsrod wynikow pojawi sie konto z flaga w polu `description`
oraz prywatne numery telefonow, ktorych nie powinno byc widac.

**Na czym polega luka:** wyszukiwarka sklada filtr
`(|(cn=FRAZA)(mail=FRAZA)(uid=FRAZA))` bez zadnego ograniczenia. Jeden znak
potrafi dopasowac wszystkie wpisy naraz.

---

## Zadanie 3: wstrzykniecie warunku OR

- **Trudnosc:** srednie
- **Czas:** okolo 15 minut
- **Ekran:** Zadanie 3: zasoby

**Cel:** w katalogu zasobow ukryto rekord, ktory nie ma nazwy (`cn`) ani dzialu
(`ou`), wiec zwykle wyszukiwanie nigdy go nie zwroci. Odczytaj flage z jego pola
`description`.

**Dowod wykonania:** w wynikach pojawi sie zasob z flaga, mimo ze nie wpisales
jego nazwy.

**Na czym polega luka:** wyszukiwarka sklada filtr `(|(cn=FRAZA)(ou=FRAZA))`.
Skoro ukryty rekord nie ma `cn` ani `ou`, sama gwiazdka go nie znajdzie. Zamknij
nawias wartosci i dopisz wlasny warunek na inny atrybut, na przyklad
`description` albo `serialNumber`. Nowy warunek musi zmiescic sie wewnatrz
istniejacego nawiasu `OR`, inaczej serwer odrzuci filtr.

Podpowiedz dotyczaca skladni: sprobuj w polu wyszukiwania wpisac cos w rodzaju
`x)(description=*`. Zobacz w podgladzie, jak zmienil sie filtr, zanim zgadniesz,
dlaczego dziala.

---

## Zadanie 4: odczyt na slepo (blind)

- **Trudnosc:** trudne
- **Czas:** okolo 15 minut
- **Ekran:** Zadanie 4: odzyskiwanie

**Cel:** formularz odzyskiwania konta mowi tylko, czy konto o podanym PIN-ie
istnieje, ale nie pokazuje zadnych danych. Odtworz 4-cyfrowy PIN konta
`aczarnecki`, a nastepnie wpisz go dokladnie, zeby odblokowac dane konta i
zobaczyc flage.

**Dowod wykonania:** po wpisaniu pelnego, poprawnego PIN-u zobaczysz flage w
danych konta.

**Na czym polega luka:** filtr ma postac `(&(uid=LOGIN)(recoveryPin=PIN))`, a PIN
trafia do niego bez obrobki. Dzieki temu dziala dopasowanie fragmentu. Sprawdzaj
kolejne cyfry prefiksem: wpisz `0*`, `1*`, ... az formularz potwierdzi, ze konto
istnieje. To daje pierwsza cyfre. Potem dopisuj kolejne, na przyklad `7*`, `74*`,
`742*`. Gdy znasz caly PIN, wpisz go bez gwiazdki.

To jest tak zwany atak na slepo (blind): serwer zdradza tajna wartosc pojedynczymi
odpowiedziami "tak/nie", mimo ze nigdy jej nie wyswietla.

---

## Po wykonaniu: przelacz na BEZPIECZNY

Kliknij **Przelacz na BEZPIECZNY** w gornym pasku i powtorz wszystkie ataki.
Zwroc uwage na to, co sie zmienia:

- **Zadanie 1:** haslo nie trafia juz do filtra. Login jest escapowany, a haslo
  sprawdza osobna operacja `bind`. Gwiazdka w hasle nic nie daje.
- **Zadanie 2:** fraza jest escapowana (gwiazdka zamienia sie na `\2a`), a filtr
  pokazuje tylko konta `public`. Rekordy `restricted` znikaja z wynikow.
- **Zadanie 3:** escapowanie zamyka droge do wstrzykniecia nawiasu, a dodatkowy
  warunek `objectClass=device` trzyma wyniki w ryzach.
- **Zadanie 4:** escapowanie blokuje dopasowanie prefiksem, a odpowiedz jest
  zawsze taka sama i ogolna. Warto pamietac, ze przy atakach na slepo samo
  escapowanie to za malo. Potrzebne sa tez ogolne komunikaty i ograniczenie
  liczby prob.
