# Laboratorium LDAP injection

Celowo podatna aplikacja webowa do nauki o wstrzykiwaniu zapytań LDAP. Całość
działa lokalnie - wbudowany serwer katalogu pracuje w pamięci, więc nie trzeba
niczego instalować poza Pythonem.

Opisy zadań i instrukcja dla uczestnika są dostępne bezpośrednio w aplikacji.


## Wymagania

- Python 3.10 lub nowszy
- Flask (jedyna zależność do uruchomienia; pytest służy do testów)

## Instalacja

```bash
git clone <adres-repo>
cd LDAP-injection-lab

python -m venv .venv
```

Aktywacja środowiska wirtualnego:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

Następnie zainstaluj zależności:

```bash
pip install -r requirements.txt
```

## Uruchomienie

```bash
python run.py
```

Aplikacja nasłuchuje na **http://127.0.0.1:5000** — otwórz ten adres
w przeglądarce.

Zatrzymanie: `Ctrl+C`.


## Struktura projektu

```
app/ldap_filter.py    parser i ewaluator filtrów LDAP (podzbiór RFC 4515)
app/directory.py      model wpisów katalogu i wczytywanie pliku LDIF
app/ldap_server.py    serwer katalogu w pamięci: search() i bind()
app/services.py       budowanie filtrów - wersja podatna i bezpieczna
app/routes.py         warstwa webowa (Flask)
app/templates/        widoki
data/seed.ldif        dane katalogu wraz z ukrytymi flagami
tests/                testy silnika filtrów i scenariuszy zadań
```
