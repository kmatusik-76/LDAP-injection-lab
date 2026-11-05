import pytest

from app.ldap_client import LdapClient


@pytest.fixture(scope="module")
def client():
    return LdapClient(backend="mock")



def test_vuln_bypass_admin_wildcard(client):
    r = client.authenticate("admin", "*", secure=False)
    assert r.ok
    assert r.dn == "uid=admin,dc=example,dc=com"
    assert r.entries[0]["description"] == "FLAG{ldapi_login_bypass_admin}"


def test_vuln_wrong_password_rejected(client):
    r = client.authenticate("admin", "zle-haslo", secure=False)
    assert not r.ok


def test_vuln_correct_login_works(client):
    r = client.authenticate("jkowalski", "Kowalski-Lab-101", secure=False)
    assert r.ok
    assert r.dn == "uid=jkowalski,ou=people,dc=example,dc=com"



def test_secure_blocks_wildcard_password(client):
    r = client.authenticate("admin", "*", secure=True)
    assert not r.ok


def test_secure_blocks_wildcard_username(client):
    r = client.authenticate("*", "*", secure=True)
    assert not r.ok


def test_secure_wrong_password_rejected(client):
    r = client.authenticate("jkowalski", "zle-haslo", secure=True)
    assert not r.ok


def test_secure_correct_login_works(client):
    r = client.authenticate("jkowalski", "Kowalski-Lab-101", secure=True)
    assert r.ok
    assert r.dn == "uid=jkowalski,ou=people,dc=example,dc=com"


def test_secure_filter_is_escaped(client):
    r = client.authenticate("*", "x", secure=True)
    assert "\\2a" in r.filter_used
    assert "uid=*" not in r.filter_used