"""Testy silnika filtrow: parsowanie, dopasowanie, escapowanie."""

import pytest

from app.directory import Entry
from app.ldap_filter import (
    FilterError,
    escape_filter_chars,
    parse_filter,
)


def make_entry(**attrs) -> Entry:
    e = Entry(dn="uid=x,dc=example,dc=com")
    for name, value in attrs.items():
        if isinstance(value, list):
            for v in value:
                e.add(name, v)
        else:
            e.add(name, value)
    return e


def matches(filter_str, entry) -> bool:
    return parse_filter(filter_str).matches(entry)


def test_equality_is_case_insensitive():
    e = make_entry(cn="Jan Kowalski")
    assert matches("(cn=jan kowalski)", e)
    assert not matches("(cn=Anna)", e)


def test_presence():
    e = make_entry(telephoneNumber="123")
    assert matches("(telephoneNumber=*)", e)
    assert not matches("(mail=*)", e)


def test_substring():
    e = make_entry(cn="Jan Kowalski")
    assert matches("(cn=Jan*)", e)
    assert matches("(cn=*kowalski)", e)
    assert matches("(cn=*an*wal*)", e)
    assert not matches("(cn=Anna*)", e)


def test_and_or_not():
    e = make_entry(cn="Jan", employeeType="public")
    assert matches("(&(cn=Jan)(employeeType=public))", e)
    assert not matches("(&(cn=Jan)(employeeType=restricted))", e)
    assert matches("(|(cn=Anna)(cn=Jan))", e)
    assert matches("(!(employeeType=restricted))", e)


def test_wildcard_password_matches_any_set_password():
    e = make_entry(userPassword="tajne-haslo")
    assert matches("(userPassword=*)", e)


def test_escaped_star_is_literal_not_wildcard():
    # Po zescapowaniu gwiazdka to zwykly znak, wiec nie dopasuje wszystkiego.
    e = make_entry(userPassword="tajne-haslo")
    escaped = escape_filter_chars("*")
    assert escaped == "\\2a"
    assert not matches(f"(userPassword={escaped})", e)
    # Doslowna gwiazdka pasuje tylko do wartosci zawierajacej gwiazdke.
    e2 = make_entry(cn="a*b")
    assert matches("(cn=a\\2ab)", e2)


def test_trailing_garbage_is_rejected():
    with pytest.raises(FilterError):
        parse_filter("(cn=a))(cn=b)")


def test_unbalanced_is_rejected():
    with pytest.raises(FilterError):
        parse_filter("(cn=a")


def test_comparison():
    e = make_entry(uidNumber="1500")
    assert matches("(uidNumber>=1000)", e)
    assert not matches("(uidNumber>=2000)", e)
