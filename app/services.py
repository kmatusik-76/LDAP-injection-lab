"""Logika aplikacji: budowanie filtrów LDAP z danych użytkownika.

Tutaj żyją podatności. Każda operacja ma dwie ścieżki:

  * PODATNA    - skleja filtr z surowych danych użytkownika (konkatenacja),
  * BEZPIECZNA - escapuje dane i zawęża zapytanie poprawnym filtrem.

Serwer (app/ldap_server.py) wykonuje oba filtry tak samo. Różnica w wyniku
bierze się wyłącznie ze sposobu, w jaki ten filtr powstał.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .ldap_filter import FilterError, escape_filter_chars
from .ldap_server import ONELEVEL, ROOT_DN, SUBTREE, MockLdapServer

PEOPLE_DN = "ou=people,dc=example,dc=com"
ASSETS_DN = "ou=assets,dc=example,dc=com"

# Etykiety trybu pokazywane w interfejsie.
VULNERABLE = "PODATNY"
SECURE = "BEZPIECZNY"

# Atrybuty pokazywane w tabelach wyników.
SHOWN_ATTRS = [
    "uid", "cn", "ou", "sn", "mail", "title", "departmentNumber",
    "telephoneNumber", "employeeType", "serialNumber", "description",
]


@dataclass
class Result:
    ok: bool
    mode: str                       # VULNERABLE albo SECURE
    filter_used: str | None = None
    base: str | None = None
    entries: list[dict] = field(default_factory=list)
    message: str = ""


def _entry_to_dict(entry, attrs: list[str]) -> dict:
    """Spłaszcza wpis do słownika wygodnego dla szablonu."""
    pairs = [(a, entry.get(a)) for a in attrs if entry.get(a)]
    return {
        "dn": entry.dn,
        "attributes": [(name, values) for name, values in pairs],
    }


class LdapApp:
    """Fasada łącząca formularze aplikacji ze zmockowanym serwerem."""

    def __init__(self, server: MockLdapServer | None = None):
        self.server = server or MockLdapServer()

    # --- Zadanie 1: logowanie ---------------------------------------------

    def login(self, username: str, password: str, secure: bool) -> Result:
        if secure:
            return self._login_secure(username, password)
        return self._login_vulnerable(username, password)

    def _login_vulnerable(self, username: str, password: str) -> Result:
        # Podatność: login i hasło wklejone do filtra bez obróbki.
        ldap_filter = f"(&(uid={username})(userPassword={password}))"
        try:
            found = self.server.search(ROOT_DN, ldap_filter, SUBTREE)
        except FilterError as exc:
            return self._rejected(ldap_filter, ROOT_DN, VULNERABLE, exc)
        if found:
            return Result(True, VULNERABLE, ldap_filter, ROOT_DN,
                          entries=[_entry_to_dict(found[0], SHOWN_ATTRS)],
                          message=f"Zalogowano jako {found[0].dn}")
        return Result(False, VULNERABLE, ldap_filter, ROOT_DN,
                      message="Błędne dane logowania.")

    def _login_secure(self, username: str, password: str) -> Result:
        # Bezpiecznie: escapujemy login, znajdujemy dokładnie jeden wpis,
        # a hasło weryfikujemy osobną operacją bind (nie w filtrze).
        safe_user = escape_filter_chars(username)
        ldap_filter = f"(&(objectClass=inetOrgPerson)(uid={safe_user}))"
        try:
            found = self.server.search(ROOT_DN, ldap_filter, SUBTREE)
        except FilterError as exc:
            return self._rejected(ldap_filter, ROOT_DN, SECURE, exc)
        if len(found) != 1 or not self.server.bind(found[0].dn, password):
            return Result(False, SECURE, ldap_filter, ROOT_DN,
                          message="Błędne dane logowania.")
        return Result(True, SECURE, ldap_filter, ROOT_DN,
                      entries=[_entry_to_dict(found[0], SHOWN_ATTRS)],
                      message=f"Zalogowano jako {found[0].dn}")

    # --- Zadanie 2: wyszukiwarka pracowników ------------------------------

    def people_search(self, query: str, secure: bool) -> Result:
        if secure:
            return self._people_secure(query)
        return self._people_vulnerable(query)

    def _people_vulnerable(self, query: str) -> Result:
        # Podatność: brak escapowania i brak filtra na employeeType.
        ldap_filter = f"(|(cn={query})(mail={query})(uid={query}))"
        return self._run_search(ldap_filter, PEOPLE_DN, VULNERABLE)

    def _people_secure(self, query: str) -> Result:
        # Bezpiecznie: escapujemy frazę i pokazujemy tylko konta publiczne.
        q = escape_filter_chars(query)
        ldap_filter = (
            f"(&(objectClass=inetOrgPerson)(employeeType=public)"
            f"(|(cn=*{q}*)(mail=*{q}*)(uid=*{q}*)))"
        )
        return self._run_search(ldap_filter, PEOPLE_DN, SECURE)

    # --- Zadanie 3: katalog zasobów ---------------------------------------

    def asset_search(self, query: str, secure: bool) -> Result:
        if secure:
            return self._asset_secure(query)
        return self._asset_vulnerable(query)

    def _asset_vulnerable(self, query: str) -> Result:
        # Podatność: fraza wklejona do filtra pozwala dopisać własny warunek.
        ldap_filter = f"(|(cn={query})(ou={query}))"
        # Zasoby leżą bezpośrednio pod ou=assets - sam kontener nie jest zasobem.
        return self._run_search(ldap_filter, ASSETS_DN, VULNERABLE, ONELEVEL)

    def _asset_secure(self, query: str) -> Result:
        q = escape_filter_chars(query)
        ldap_filter = f"(&(objectClass=device)(|(cn=*{q}*)(ou=*{q}*)))"
        return self._run_search(ldap_filter, ASSETS_DN, SECURE, ONELEVEL)

    # --- Zadanie 4: odzyskiwanie konta (blind) ----------------------------

    def recovery(self, uid: str, pin: str, secure: bool) -> Result:
        if secure:
            return self._recovery_secure(uid, pin)
        return self._recovery_vulnerable(uid, pin)

    def _recovery_vulnerable(self, uid: str, pin: str) -> Result:
        # Podatność: PIN wklejony do filtra pozwala dopasować fragment (prefiks).
        ldap_filter = f"(&(uid={uid})(recoveryPin={pin}))"
        try:
            found = self.server.search(PEOPLE_DN, ldap_filter, SUBTREE)
        except FilterError as exc:
            return self._rejected(ldap_filter, PEOPLE_DN, VULNERABLE, exc)
        if not found:
            return Result(False, VULNERABLE, ldap_filter, PEOPLE_DN,
                          message="Nie znaleziono konta o podanych danych.")
        # Flagę odsłaniamy tylko przy dokładnym PIN-ie (bez znaku wieloznacznego).
        if "*" in pin:
            return Result(True, VULNERABLE, ldap_filter, PEOPLE_DN,
                          message="Konto o podanych danych istnieje.")
        return Result(True, VULNERABLE, ldap_filter, PEOPLE_DN,
                      entries=[_entry_to_dict(found[0], SHOWN_ATTRS + ["recoveryFlag"])],
                      message="PIN poprawny. Odblokowano dane konta.")

    def _recovery_secure(self, uid: str, pin: str) -> Result:
        # Bezpiecznie: escapujemy oba pola i zawsze zwracamy tę samą,
        # ogólną odpowiedź (brak wyciekania przez treść komunikatu).
        safe_uid = escape_filter_chars(uid)
        safe_pin = escape_filter_chars(pin)
        ldap_filter = f"(&(uid={safe_uid})(recoveryPin={safe_pin}))"
        try:
            self.server.search(PEOPLE_DN, ldap_filter, SUBTREE)
        except FilterError as exc:
            return self._rejected(ldap_filter, PEOPLE_DN, SECURE, exc)
        return Result(True, SECURE, ldap_filter, PEOPLE_DN,
                      message="Jeśli dane są poprawne, wyślemy instrukcje na e-mail.")

    # --- Wspólny wykonawca wyszukiwania -----------------------------------

    def _run_search(self, ldap_filter: str, base: str, mode: str,
                    scope: str = SUBTREE) -> Result:
        try:
            found = self.server.search(base, ldap_filter, scope)
        except FilterError as exc:
            return self._rejected(ldap_filter, base, mode, exc)
        return Result(True, mode, ldap_filter, base,
                      entries=[_entry_to_dict(e, SHOWN_ATTRS) for e in found],
                      message=f"Znaleziono wpisów: {len(found)}")

    @staticmethod
    def _rejected(ldap_filter: str, base: str, mode: str, exc: FilterError) -> Result:
        """Serwer nie przyjął filtra - pokazujemy, dlaczego go odrzucił."""
        return Result(False, mode, ldap_filter, base,
                      message=f"Serwer odrzucił filtr: {exc}")
