# Laboratorium LDAP injection

Celowo podatna aplikacja webowa do nauki o wstrzykiwaniu zapytan LDAP. To projekt
edukacyjny, w pelni lokalny, bez zadnego prawdziwego serwera na zewnatrz. Kod jest
jawny (podejscie white-box), bo chodzi o to, zeby zrozumiec, dlaczego atak dziala
i jak go naprawic, a nie tylko go wykonac.

Aplikacja udaje wewnetrzny system firmy i ma kilka ekranow, w ktorych dane
uzytkownika trafiaja wprost do filtra LDAP. U gory kazdej strony jest przelacznik
**PODATNY / BEZPIECZNY**. W trybie podatnym ataki dzialaja, w bezpiecznym te same
ataki juz nie dzialaja. Na kazdym ekranie pokazujemy dokladny filtr wyslany do
serwera oraz to, jak serwer go rozumie, zeby roznica byla widoczna.

> Uwaga: kod zawiera swiadome luki (sklejanie danych wejsciowych z filtrem,
> hasla trzymane jawnie, brak ograniczenia zakresu wyszukiwania). To wzorce,
> ktorych nigdy nie wolno uzywac w prawdziwej aplikacji.

## Jak to dziala pod spodem

Nie korzystamy z zewnetrznej biblioteki LDAP. Serwer jest napisany od zera i
dziala w pamieci, dzieki czemu calosc jest lokalna, przewidywalna i latwa do
czytania. Sklada sie z kilku prostych czesci:

- `app/ldap_filter.py` - parser i ewaluator filtrow LDAP (podzbior RFC 4515).
  To tutaj napis z filtrem zamienia sie w drzewo warunkow. Wstrzykniecie dziala,
  bo zmienia ksztalt tego drzewa.
- `app/directory.py` - model wpisow katalogu i wczytywanie danych z pliku LDIF.
- `app/ldap_server.py` - zmockowany serwer: `search()` i `bind()`. Nie wie nic
  o atakach, po prostu wykonuje filtr.
- `app/services.py` - logika aplikacji, czyli miejsce, w ktorym powstaja filtry.
  Kazda operacja ma wersje podatna i bezpieczna.
- `app/routes.py`, `app/templates/` - cienka warstwa webowa (Flask).
- `data/seed.ldif` - dane katalogu wraz z ukrytymi flagami.

## Uruchomienie

Potrzebny jest tylko **Python 3.9 lub nowszy**. Jedyna zaleznosc do dzialania to
Flask (pytest sluzy do testow).

```bash
git clone <adres-repo>
cd LDAP-injection-lab

python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
python run.py
```

Otworz w przegladarce **http://127.0.0.1:5000**.

## Jak korzystac z laboratorium

1. Zacznij na stronie startowej. Jest tam lista zadan z celami i szacowanym czasem.
2. Pracuj w trybie **PODATNY** (czerwony pasek). Zdobadz flagi w formacie `FLAG{...}`.
3. Pod kazdym formularzem obejrzyj filtr wyslany do serwera i rozwin sekcje
   "Jak serwer rozumie ten filtr". To najlepsza podpowiedz.
4. Jesli chcesz przecwiczyc skladnie filtrow bez ryzyka, uzyj **Konsoli LDAP**.
   Odpytuje ona osobne poddrzewo z przykladowymi danymi (bez flag).
5. Zdobyta flage mozesz potwierdzic na stronie **Sprawdz flage**.
6. Na koniec przelacz na tryb **BEZPIECZNY** (zielony pasek) i powtorz ataki.
   Zobacz, jak zmienia sie filtr i dlaczego atak przestaje dzialac.

Pelna lista zadan wraz z celami jest w pliku [ZADANIA.md](ZADANIA.md).

## Testy

```bash
pip install -r requirements.txt
pytest
```

Testy sprawdzaja dwie rzeczy: ze silnik filtrow dziala poprawnie oraz ze w trybie
podatnym kazdy atak zdobywa swoja flage, a w trybie bezpiecznym jest blokowany.

## Czego uczy to laboratorium

- Dlaczego sklejanie zapytania z danych uzytkownika prowadzi do wstrzykniecia.
- Jak znaki specjalne (`*`, `(`, `)`) zmieniaja znaczenie filtra.
- Na czym polega escapowanie wartosci i dlaczego samo escapowanie czasem nie
  wystarcza (patrz Zadanie 4).
- Dlaczego autoryzacje i weryfikacje hasla trzeba robic poza filtrem (operacja
  bind, a nie warunek `userPassword=...`).
- Dlaczego warto zawezac zakres wyszukiwania i ograniczac zwracane atrybuty.
