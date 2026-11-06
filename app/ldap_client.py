from __future__ import annotations

import base64
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

from ldap3 import (
    Server,
    Connection,
    MOCK_SYNC,
    OFFLINE_SLAPD_2_4,
    ALL,
    SUBTREE,
    ALL_ATTRIBUTES,
)
from ldap3.utils.conv import escape_filter_chars

BASE_DN = "dc=example,dc=com"
PEOPLE_DN = "ou=people,dc=example,dc=com"
SERVICE_DN = "cn=svc-webapp,dc=example,dc=com"
SERVICE_PW = os.environ.get("LDAP_SERVICE_PW", "svc-webapp-lab-only")


SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed.ldif"

SHOWN_ATTRS = [
    "uid", "cn", "sn", "mail", "title", "departmentNumber",
    "telephoneNumber", "employeeType", "description",
]

def parse_ldif(path: Path) -> list[tuple[str, dict[str, list[str]]]]:
    """Minimalny, ale poprawny parser LDIF dla naszego seeda.

    Obsluguje: komentarze (#), puste linie jako separator wpisow,
    zawijanie linii (kontynuacja zaczyna sie od spacji) oraz wartosci
    base64 (atrybut zapisany jako 'name:: <base64>').
    Nie obsluguje rekordow zmian (changetype) - seed ich nie uzywa.
    """
    entries: list[tuple[str, dict[str, list[str]]]] = []
    dn: str | None = None
    attrs: dict[str, list[str]] = {}

    def flush():
        nonlocal dn, attrs
        if dn is not None:
            entries.append((dn, attrs))
        dn, attrs = None, {}

    raw_lines = path.read_text(encoding="utf-8").splitlines()
    logical: list[str] = []
    for line in raw_lines:
        if line.startswith(" ") and logical:
            logical[-1] += line[1:]
        else:
            logical.append(line)

    for line in logical:
        if line.startswith("#"):
            continue
        if line.strip() == "":
            flush()
            continue
        if "::" in line and line.split("::", 1)[0].isidentifier():
            key, b64 = line.split("::", 1)
            value = base64.b64decode(b64.strip()).decode("utf-8")
        else:
            key, value = line.split(":", 1)
            value = value.lstrip()
        key = key.strip()
        if key == "dn":
            flush()
            dn = value
        else:
            attrs.setdefault(key, []).append(value)
    flush()
    return entries


@dataclass
class LdapResult:
    ok: bool
    filter_used: str
    mode: str                      
    dn: str | None = None
    entries: list[dict] = field(default_factory=list)
    message: str = ""


class LdapClient:
    def __init__(self, backend: str | None = None):
        self.backend = (backend or os.environ.get("LDAP_BACKEND", "mock")).lower()
        self._lock = threading.Lock()   
        self._svc_conn: Connection | None = None
        if self.backend == "mock":
            self._server = self._build_mock_server()
        elif self.backend == "docker":
            uri = os.environ.get("LDAP_URI", "ldap://localhost:389")
            self._server = Server(uri, get_info=ALL)
        else:
            raise ValueError(f"Nieznany backend LDAP: {self.backend!r} (uzyj 'mock' lub 'docker')")

    def _build_mock_server(self) -> Server:
        server = Server("mock-server", get_info=OFFLINE_SLAPD_2_4)
        conn = Connection(server, user=SERVICE_DN, password=SERVICE_PW, client_strategy=MOCK_SYNC)
        for dn, attrs in parse_ldif(SEED_PATH):
            if not conn.strategy.add_entry(dn, attrs):
                raise RuntimeError(f"Nie udalo sie zaladowac wpisu: {dn} ({conn.result})")
        if not conn.bind():
            raise RuntimeError(f"Bind konta serwisowego do MOCK nie powiodl sie: {conn.result}")
        self._svc_conn = conn
        return server

    def _search(self, base: str, ldap_filter: str) -> list:
        if self.backend == "mock":
            with self._lock:
                self._svc_conn.search(base, ldap_filter, SUBTREE, attributes=ALL_ATTRIBUTES)
                return list(self._svc_conn.entries)
        # docker: swieze polaczenie na operacje
        conn = Connection(self._server, user=SERVICE_DN, password=SERVICE_PW, auto_bind=True)
        try:
            conn.search(base, ldap_filter, SUBTREE, attributes=ALL_ATTRIBUTES)
            return list(conn.entries)
        finally:
            conn.unbind()

    def _try_bind(self, dn: str, password: str) -> bool:
        if self.backend == "mock":
            conn = Connection(self._server, user=dn, password=password, client_strategy=MOCK_SYNC)
        else:
            conn = Connection(self._server, user=dn, password=password)
        ok = conn.bind()
        if ok:
            conn.unbind()
        return ok

    @staticmethod
    def _entry_to_dict(entry) -> dict:
        d = entry.entry_attributes_as_dict
        flat = {"dn": entry.entry_dn}
        for k in SHOWN_ATTRS:
            v = d.get(k)
            flat[k] = v[0] if isinstance(v, list) and len(v) == 1 else v
        return flat

    def authenticate(self, username: str, password: str, secure: bool) -> LdapResult:
        if secure:
            return self._authenticate_secure(username, password)
        return self._authenticate_vulnerable(username, password)

    def _authenticate_vulnerable(self, username: str, password: str) -> LdapResult:
        ldap_filter = f"(&(objectClass=inetOrgPerson)(uid={username})(userPassword={password}))"
        try:
            found = self._search(BASE_DN, ldap_filter)
        except Exception as exc:  
            return LdapResult(False, ldap_filter, "PODATNY",
                              message=f"Serwer odrzucil filtr: {type(exc).__name__}")

        if found:
            e = found[0]
            return LdapResult(True, ldap_filter, "PODATNY", dn=e.entry_dn,
                              entries=[self._entry_to_dict(e)],
                              message=f"Zalogowano jako {e.entry_dn}")
        return LdapResult(False, ldap_filter, "PODATNY", message="Bledne dane logowania")

    def _authenticate_secure(self, username: str, password: str) -> LdapResult:
        safe_user = escape_filter_chars(username)
        ldap_filter = f"(&(objectClass=inetOrgPerson)(uid={safe_user}))"
        found = self._search(BASE_DN, ldap_filter)

        if len(found) != 1:
            return LdapResult(False, ldap_filter, "BEZPIECZNY",
                              message="Bledne dane logowania")  #
        entry = found[0]
        if not password or not self._try_bind(entry.entry_dn, password):
            return LdapResult(False, ldap_filter, "BEZPIECZNY", message="Bledne dane logowania")
        return LdapResult(True, ldap_filter, "BEZPIECZNY", dn=entry.entry_dn,
                          entries=[self._entry_to_dict(entry)],
                          message=f"Zalogowano jako {entry.entry_dn}")

    def search_people(self, query: str, secure: bool) -> LdapResult:
        if secure:
            return self._search_secure(query)
        return self._search_vulnerable(query)

    def _search_vulnerable(self, query: str) -> LdapResult:
        ldap_filter = f"(|(cn={query})(mail={query})(uid={query}))"
        try:
            results = [self._entry_to_dict(e) for e in self._search(BASE_DN, ldap_filter)]
        except Exception as exc:
            return LdapResult(False, ldap_filter, "PODATNY",
                              message=f"Serwer odrzucil filtr: {type(exc).__name__}")
        return LdapResult(True, ldap_filter, "PODATNY", entries=results,
                          message=f"Znaleziono {len(results)} wpisow")

    def _search_secure(self, query: str) -> LdapResult:
        q = escape_filter_chars(query)
        ldap_filter = (
            f"(&(objectClass=inetOrgPerson)(employeeType=public)"
            f"(|(cn=*{q}*)(mail=*{q}*)))"
        )
        results = [self._entry_to_dict(e) for e in self._search(PEOPLE_DN, ldap_filter)]
        return LdapResult(True, ldap_filter, "BEZPIECZNY", entries=results,
                          message=f"Znaleziono {len(results)} wpisow")


def _demo():
    client = LdapClient(backend=os.environ.get("LDAP_BACKEND", "mock"))
    print(f"# Backend: {client.backend}\n")

    def show(title, r: LdapResult):
        print(f"== {title} [{r.mode}] ==")
        print(f"   filtr : {r.filter_used}")
        print(f"   wynik : ok={r.ok}  {r.message}")
        for e in r.entries:
            desc = e.get("description") or ""
            flag = f"  <-- {desc}" if desc.startswith("FLAG{") else ""
            print(f"           {e['dn']}{flag}")
        print()

    print("### ZADANIE 1: bypass logowania ###")
    show("admin/haslo (poprawne? nie znamy) -> probujemy '*'",
         client.authenticate("admin", "*", secure=False))
    show("to samo w trybie BEZPIECZNYM",
         client.authenticate("admin", "*", secure=True))

    print("### ZADANIE 2: wyciek wildcardem ###")
    show("szukaj '*' (PODATNY) - caly katalog",
         client.search_people("*", secure=False))
    show("szukaj '*' (BEZPIECZNY) - tylko publiczni",
         client.search_people("*", secure=True))


if __name__ == "__main__":
    _demo()