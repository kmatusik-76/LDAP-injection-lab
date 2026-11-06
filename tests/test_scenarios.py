"""Testy scenariuszy: w trybie PODATNYM atak dziala, w BEZPIECZNYM nie."""

import pytest

from app.scenarios import SCENARIOS
from app.services import LdapApp


@pytest.fixture()
def app():
    return LdapApp()


def flags_in(result):
    found = set()
    for e in result.entries:
        for _, values in e["attributes"]:
            for v in values:
                if v.startswith("FLAG{"):
                    found.add(v)
    return found


# --- Zadanie 1: ominiecie logowania ---------------------------------------

def test_login_bypass_with_wildcard_password(app):
    r = app.login("admin", "*", secure=False)
    assert r.ok
    assert "FLAG{ldap_login_bypass_wildcard}" in flags_in(r)


def test_login_correct_password_still_works(app):
    r = app.login("jkowalski", "Kowalski-Lab-101", secure=False)
    assert r.ok


def test_login_wrong_password_rejected(app):
    r = app.login("admin", "zle-haslo", secure=False)
    assert not r.ok


def test_login_secure_blocks_wildcard(app):
    # Haslo "*" nie trafia do filtra (sprawdza je bind), wiec logowanie pada.
    assert not app.login("admin", "*", secure=True).ok
    # Gdy gwiazdka jest w loginie, escapowanie zamienia ja na \2a.
    r = app.login("*", "x", secure=True)
    assert not r.ok
    assert "\\2a" in r.filter_used


def test_login_secure_requires_real_password(app):
    assert not app.login("jkowalski", "*", secure=True).ok
    assert app.login("jkowalski", "Kowalski-Lab-101", secure=True).ok


# --- Zadanie 2: wyciek ksiazki adresowej ----------------------------------

def test_people_wildcard_leaks_restricted(app):
    r = app.people_search("*", secure=False)
    assert r.ok
    assert "FLAG{ldap_wildcard_directory_dump}" in flags_in(r)


def test_people_secure_hides_restricted(app):
    r = app.people_search("*", secure=True)
    assert "FLAG{ldap_wildcard_directory_dump}" not in flags_in(r)
    assert "\\2a" in r.filter_used


def test_people_secure_normal_search_works(app):
    r = app.people_search("Nowak", secure=True)
    uids = {v for e in r.entries for n, vals in e["attributes"] if n == "uid" for v in vals}
    assert "anowak" in uids


# --- Zadanie 3: wstrzykniecie warunku OR ----------------------------------

def test_assets_plain_wildcard_does_not_reveal_hidden(app):
    # Ukryty zasob nie ma cn ani ou, wiec sam '*' go nie znajdzie.
    r = app.asset_search("*", secure=False)
    assert "FLAG{ldap_or_attribute_injection}" not in flags_in(r)


def test_assets_or_injection_reveals_hidden(app):
    r = app.asset_search("x)(description=*", secure=False)
    assert r.ok
    assert "FLAG{ldap_or_attribute_injection}" in flags_in(r)


def test_assets_secure_blocks_injection(app):
    r = app.asset_search("x)(description=*", secure=True)
    assert "FLAG{ldap_or_attribute_injection}" not in flags_in(r)


# --- Zadanie 4: odczyt na slepo --------------------------------------------

def test_recovery_prefix_oracle_leaks_without_showing_data(app):
    r = app.recovery("aczarnecki", "7*", secure=False)
    assert r.ok
    assert flags_in(r) == set()  # oracle mowi tylko "istnieje", bez danych


def test_recovery_wrong_prefix_not_found(app):
    assert not app.recovery("aczarnecki", "1*", secure=False).ok


def test_recovery_exact_pin_reveals_flag(app):
    r = app.recovery("aczarnecki", "7429", secure=False)
    assert r.ok
    assert "FLAG{ldap_blind_pin_extraction}" in flags_in(r)


def test_recovery_secure_never_reveals_and_escapes(app):
    r = app.recovery("aczarnecki", "7*", secure=True)
    assert flags_in(r) == set()
    assert "\\2a" in r.filter_used


# --- Spojnosc danych --------------------------------------------------------

def test_every_scenario_flag_is_reachable():
    # Pilnuje, ze flagi w opisach zadan zgadzaja sie z danymi w seedzie.
    app = LdapApp()
    reachable = set()
    reachable |= flags_in(app.login("admin", "*", secure=False))
    reachable |= flags_in(app.people_search("*", secure=False))
    reachable |= flags_in(app.asset_search("x)(description=*", secure=False))
    reachable |= flags_in(app.recovery("aczarnecki", "7429", secure=False))
    for s in SCENARIOS:
        assert s.flag in reachable, f"Flaga zadania {s.id} nieosiagalna: {s.flag}"
