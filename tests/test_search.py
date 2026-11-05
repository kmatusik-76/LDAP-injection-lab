import pytest 
from app.ldap_client import LdapClient

LEAK_FLAG = "FLAG_{ldapi_wildcard_directory_leak}"

@pytest.fixture(scope="module")
def client():
    return LdapClient(backend="mock")

def _uids(result):
    return {e["uid"] for e in result.entries if e.get("uid")}

def _descriptions(result):
    return {e.get("description") for e in result.entries}

def test_vuln_wildcard_leaks_whole_directory(client):
    r = client.search_people("*", secure=False)
    assert r.ok
    uids = _uids(r)
    assert "jkowalski" in uids
    assert "kdabrowski" in uids
    assert "elewandowska" in uids

def test_vuln_wildcard_exposes_flag(client):
    r = client.search_people("*", secure=False)
    assert LEAK_FLAG in _descriptions(r)

def test_vuln_normal_search_still_works(client):
    r = client.search_people("*nowak*", secure=False)
    assert "anowak" in _uids(r)




def test_secure_wildcard_returns_only_public(client):
    r = client.search_people("*", secure=False)  
    r_safe = client.search_people("*", secure=True)
    assert _uids(r_safe) == {"jkowalski", "anowak", "pwisniewski", "mzielinska", "tkaminski"}
    assert len(_uids(r_safe)) < len(_uids(r))


def test_secure_never_leaks_restricted(client):
    r = client.search_people("*", secure=True)
    assert LEAK_FLAG not in _descriptions(r)
    for e in r.entries:
        assert e.get("employeeType") != "restricted"


def test_secure_escapes_wildcard(client):
    r = client.search_people("*", secure=True)
    assert "\\2a" in r.filter_used
    assert "employeeType=public" in r.filter_used


def test_secure_substring_search_works(client):
    r = client.search_people("Nowak", secure=True)
    assert "anowak" in _uids(r)
