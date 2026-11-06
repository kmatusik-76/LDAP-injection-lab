# Laboratorium LDAP injection

Celowo podatna aplikacja webowa do nauki **LDAP injection**. Projekt edukacyjny
(white-box) — kod jest jawny, a celem jest zrozumienie, *dlaczego* atak działa
i jak go naprawić.

Aplikacja ma dwa ekrany — **logowanie** i **wyszukiwarkę pracowników** — oraz
przełącznik **PODATNY / BEZPIECZNY** w górnym banerze. Ten sam formularz w trybie
podatnym da się zaatakować, a w bezpiecznym nie. Na każdym ekranie pokazywany jest
**dokładny filtr LDAP** wysłany do serwera, żeby było widać różnicę.

> ⚠️ **Tylko do nauki.** Kod zawiera świadome luki (konkatenacja wejścia do
> filtra LDAP, hasła jawnym tekstem, brak filtra autoryzacji). Nigdy nie używaj
> takich wzorców w produkcji.

## Uruchomienie 

Wymagany tylko **Python 3.9+**. Serwer LDAP działa w pamięci (`ldap3` w trybie
`MOCK_SYNC`), dane ładowane są z [`data/seed.ldif`](data/seed.ldif) — nie trzeba
niczego instalować poza zależnościami z `requirements.txt`.

```bash
git clone <adres-repo>
cd ldap-injection-lab

python -m venv venv
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
python run.py
```

Otwórz **http://127.0.0.1:5000**.