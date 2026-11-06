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

Aplikacja nasłuchuje na **http://127.0.0.1:5000** - otwórz ten adres
w przeglądarce.

Zatrzymanie: `Ctrl+C`.


## Struktura projektu

```
LDAP-injection-lab/
├── run.py                  # punkt startowy – uruchamia serwer Flask
├── requirements.txt        # zależności (Flask, pytest)
├── data/
│   └── seed.ldif           # dane katalogu LDAP 
├── app/
│   ├── __init__.py         # fabryka aplikacji Flask
│   ├── routes.py           # warstwa webowa – adresy URL i obsługa formularzy
│   ├── services.py         # budowanie filtrów: wersja PODATNA vs BEZPIECZNA
│   ├── ldap_server.py      # serwer katalogu w pamięci: search() i bind()
│   ├── ldap_filter.py      # parser i ewaluator filtrów LDAP (serce labu)
│   ├── directory.py        # model wpisów + wczytywanie pliku LDIF
│   ├── scenarios.py        # opisy 4 zadań 
│   ├── static/
│   │   └── style.css       # style
│   └── templates/          # widoki HTML (Jinja2)
└── tests/                  # testy silnika filtrów i scenariuszy
```

## Struktura katalogu LDAP (DIT)

Dane pochodzą z pliku `data/seed.ldif`. Poniżej podano RDN każdego wpisu -
pełny DN powstaje przez doklejenie DN-ów rodziców, np.
`uid=jkowalski,ou=people,dc=example,dc=com`.

```
dc=example,dc=com                      # korzeń organizacji (Example Sp. z o.o.)
├── uid=admin                          # konto administratora
├── cn=svc-webapp                      # konto serwisowe aplikacji
│
├── ou=people                          # pracownicy (książka adresowa)
│   ├── uid=jkowalski                  # Jan Kowalski
│   ├── uid=anowak                     # Anna Nowak
│   ├── uid=pwisniewski                # Piotr Wisniewski
│   ├── uid=mzielinska                 # Maria Zielinska
│   ├── uid=tkaminski                  # Tomasz Kaminski
│   ├── uid=elewandowska               # Ewa Lewandowska
│   ├── uid=kdabrowski                 # Krzysztof Dabrowski
│   └── uid=aczarnecki                 # Adam Czarnecki
│
└── ou=assets                          # zasoby / urządzenia sieciowe
    ├── cn=drukarka-hr                 # drukarka sieciowa w dziale HR
    ├── cn=serwer-vpn                  # brama VPN
    └── serialNumber=KEY-7731          # zasób bez atrybutów cn i ou
```

Katalog dzieli się na dwa poddrzewa: `ou=people` (konta pracowników)
i `ou=assets` (urządzenia). Pod korzeniem znajdują się też konto
administratora i konto serwisowe aplikacji.
