"""Logika aplikacji: budowanie filtrow LDAP z danych uzytkownika.

Tutaj zyja podatnosci. Kazda operacja ma dwie sciezki:

  * PODATNA   - skleja filtr z surowych danych uzytkownika (konkatenacja),
  * BEZPIECZNA - escapuje dane i zaweza zapytanie poprawnym filtrem.

Serwer (app/ldap_server.py) wykonuje oba filtry tak samo. Roznica w wyniku
bierze sie wylacznie ze sposobu, w jaki ten filtr powstal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .ldap_filter import FilterError, escape_filter_chars
from .ldap_server import ONELEVEL, ROOT_DN, SUBTREE, MockLdapServer

PEOPLE_DN = "ou=people,dc=example,dc=com"
ASSETS_DN = "ou=assets,dc=example,dc=com"
SANDBOX_DN = "ou=sandbox,dc=example,dc=com"

# Atrybuty pokazywane w tabelach wynikow (poza konsola, ktora pokazuje wszystko).
SHOWN_ATTRS = [
    "uid", "cn", "sn", "mail", "title", "departmentNumber",
    "telephoneNumber", "employeeType", "serialNumber", "description",
]


@dataclass
class Result:
    ok: bool
    mode: str                       # "PODATNY" albo "BEZPIECZNY"
    filter_used: str | None = None
    base: str | None = None
    entries: list[dict] = field(default_factory=list)
    message: str = ""


def _entry_to_dict(entry, attrs: list[str] | None = None) -> dict:
    """Splaszcza wpis do slownika wygodnego dla szablonu."""
    if attrs is None:
        pairs = list(entry.attributes)
    else:
        pairs = [(a, entry.get(a)) for a in attrs if entry.get(a)]
    flag = None
    for _, values in pairs:
        for v in values:
            if v.startswith("FLAG{"):
                flag = v
    return {
        "dn": entry.dn,
        "attributes": [(name, values) for name, values in pairs],
        "flag": flag,
    }


class LdapApp:
    """Fasada laczaca formularze aplikacji ze zmockowanym serwerem."""

    def __init__(self, server: MockLdapServer | None = None):
        self.server = server or MockLdapServer()

    # --- Zadanie 1: logowanie ---------------------------------------------

    def login(self, username: str, password: str, secure: bool) -> Result:
        if secure:
            return self._login_secure(username, password)
        return self._login_vulnerable(username, password)

    def _login_vulnerable(self, username: str, password: str) -> Result:
        # Podatnosc: login i haslo wklejone do filtra bez obrobki.
        ldap_filter = f"(&(uid={username})(userPassword={password}))"
        try:
            found = self.server.search(ROOT_DN, ldap_filter, SUBTREE)
        except FilterError as exc:
            return Result(False, "PODATNY", ldap_filter, ROOT_DN,
                          message=f"Serwer odrzucil filtr: {exc}")
        if found:
            return Result(True, "PODATNY", ldap_filter, ROOT_DN,
                          entries=[_entry_to_dict(found[0], SHOWN_ATTRS)],
                          message=f"Zalogowano jako {found[0].dn}")
        return Result(False, "PODATNY", ldap_filter, ROOT_DN,
                      message="Bledne dane logowania.")

    def _login_secure(self, username: str, password: str) -> Result:
        # Bezpiecznie: escapujemy login, znajdujemy dokladnie jeden wpis,
        # a haslo weryfikujemy osobna operacja bind (nie w filtrze).
        safe_user = escape_filter_chars(username)
        ldap_filter = f"(&(objectClass=inetOrgPerson)(uid={safe_user}))"
        found = self.server.search(ROOT_DN, ldap_filter, SUBTREE)
        if len(found) != 1 or not self.server.bind(found[0].dn, password):
            return Result(False, "BEZPIECZNY", ldap_filter, ROOT_DN,
                          message="Bledne dane logowania.")
        return Result(True, "BEZPIECZNY", ldap_filter, ROOT_DN,
                      entries=[_entry_to_dict(found[0], SHOWN_ATTRS)],
                      message=f"Zalogowano jako {found[0].dn}")

    # --- Zadanie 2: wyszukiwarka pracownikow ------------------------------

    def people_search(self, query: str, secure: bool) -> Result:
        if secure:
            return self._people_secure(query)
        return self._people_vulnerable(query)

    def _people_vulnerable(self, query: str) -> Result:
        # Podatnosc: brak escapowania i brak filtra na employeeType.
        ldap_filter = f"(|(cn={query})(mail={query})(uid={query}))"
        return self._run_search(ldap_filter, PEOPLE_DN, "PODATNY")

    def _people_secure(self, query: str) -> Result:
        # Bezpiecznie: escapujemy fraze i pokazujemy tylko konta publiczne.
        q = escape_filter_chars(query)
        ldap_filter = (
            f"(&(objectClass=inetOrgPerson)(employeeType=public)"
            f"(|(cn=*{q}*)(mail=*{q}*)(uid=*{q}*)))"
        )
        return self._run_search(ldap_filter, PEOPLE_DN, "BEZPIECZNY")

    # --- Zadanie 3: katalog zasobow ---------------------------------------

    def asset_search(self, query: str, secure: bool) -> Result:
        if secure:
            return self._asset_secure(query)
        return self._asset_vulnerable(query)

    def _asset_vulnerable(self, query: str) -> Result:
        # Podatnosc: fraza wklejona do filtra pozwala dopisac wlasny warunek.
        ldap_filter = f"(|(cn={query})(ou={query}))"
        return self._run_search(ldap_filter, ASSETS_DN, "PODATNY")

    def _asset_secure(self, query: str) -> Result:
        q = escape_filter_chars(query)
        ldap_filter = f"(&(objectClass=device)(|(cn=*{q}*)(ou=*{q}*)))"
        return self._run_search(ldap_filter, ASSETS_DN, "BEZPIECZNY")

    # --- Zadanie 4: odzyskiwanie konta (blind) ----------------------------

    def recovery(self, uid: str, pin: str, secure: bool) -> Result:
        if secure:
            return self._recovery_secure(uid, pin)
        return self._recovery_vulnerable(uid, pin)

    def _recovery_vulnerable(self, uid: str, pin: str) -> Result:
        # Podatnosc: PIN wklejony do filtra pozwala dopasowac fragment (prefiks).
        ldap_filter = f"(&(uid={uid})(recoveryPin={pin}))"
        try:
            found = self.server.search(PEOPLE_DN, ldap_filter, SUBTREE)
        except FilterError as exc:
            return Result(False, "PODATNY", ldap_filter, PEOPLE_DN,
                          message=f"Serwer odrzucil filtr: {exc}")
        if not found:
            return Result(False, "PODATNY", ldap_filter, PEOPLE_DN,
                          message="Nie znaleziono konta o podanych danych.")
        # Flage odslaniamy tylko przy dokladnym PIN-ie (bez znaku wieloznacznego).
        if "*" in pin:
            return Result(True, "PODATNY", ldap_filter, PEOPLE_DN,
                          message="Konto o podanych danych istnieje.")
        return Result(True, "PODATNY", ldap_filter, PEOPLE_DN,
                      entries=[_entry_to_dict(found[0], SHOWN_ATTRS + ["recoveryFlag"])],
                      message="PIN poprawny. Odblokowano dane konta.")

    def _recovery_secure(self, uid: str, pin: str) -> Result:
        # Bezpiecznie: escapujemy oba pola i zawsze zwracamy te sama,
        # ogolna odpowiedz (brak wyciekania przez tresc komunikatu).
        safe_uid = escape_filter_chars(uid)
        safe_pin = escape_filter_chars(pin)
        ldap_filter = f"(&(uid={safe_uid})(recoveryPin={safe_pin}))"
        self.server.search(PEOPLE_DN, ldap_filter, SUBTREE)
        return Result(True, "BEZPIECZNY", ldap_filter, PEOPLE_DN,
                      message="Jesli dane sa poprawne, wyslemy instrukcje na e-mail.")

    # --- Konsola: piaskownica do cwiczenia skladni filtrow ----------------

    def console_query(self, ldap_filter: str) -> Result:
        # Konsola odpytuje wylacznie poddrzewo piaskownicy (bez flag), zeby
        # mozna bylo swobodnie cwiczyc skladnie filtrow.
        try:
            found = self.server.search(SANDBOX_DN, ldap_filter, SUBTREE)
        except FilterError as exc:
            return Result(False, "KONSOLA", ldap_filter, SANDBOX_DN,
                          message=f"Serwer odrzucil filtr: {exc}")
        return Result(True, "KONSOLA", ldap_filter, SANDBOX_DN,
                      entries=[_entry_to_dict(e) for e in found],
                      message=f"Znaleziono wpisow: {len(found)}")

    # --- Wspolny wykonawca wyszukiwania -----------------------------------

    def _run_search(self, ldap_filter: str, base: str, mode: str) -> Result:
        try:
            found = self.server.search(base, ldap_filter, SUBTREE)
        except FilterError as exc:
            return Result(False, mode, ldap_filter, base,
                          message=f"Serwer odrzucil filtr: {exc}")
        return Result(True, mode, ldap_filter, base,
                      entries=[_entry_to_dict(e, SHOWN_ATTRS) for e in found],
                      message=f"Znaleziono wpisow: {len(found)}")
