"""Testy stron: opisy zadań są widoczne w aplikacji, a kod w nich bezpiecznie sformatowany."""

import pytest

from app import create_app
from app.scenarios import SCENARIOS


@pytest.fixture()
def client():
    return create_app().test_client()


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)
def test_task_page_shows_full_description(client, scenario):
    html = client.get(f"/{scenario.endpoint.split('.')[1]}").get_data(as_text=True)
    assert scenario.title in html
    for label in ("Cel:", "Na czym polega luka", "Podpowiedź"):
        assert label in html


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)
def test_secure_note_only_in_secure_mode(client, scenario):
    url = f"/{scenario.endpoint.split('.')[1]}"
    # Domyślnie aplikacja jest w trybie PODATNY - sekcji nie ma.
    html = client.get(url).get_data(as_text=True)
    assert "Co zmienia tryb BEZPIECZNY" not in html

    client.post("/toggle", data={"next": url})
    html = client.get(url).get_data(as_text=True)
    assert "Co zmienia tryb BEZPIECZNY" in html


def test_index_lists_all_tasks(client):
    html = client.get("/").get_data(as_text=True)
    for s in SCENARIOS:
        assert s.title in html


def test_inline_code_is_rendered_and_escaped(client):
    html = client.get("/login").get_data(as_text=True)
    # Fragment w `...` staje się <code>, a znaki specjalne są escapowane.
    assert "<code>(&amp;(uid=TWÓJ_LOGIN)(userPassword=TWOJE_HASŁO))</code>" in html


def test_directory_page_shows_tree(client):
    html = client.get("/directory").get_data(as_text=True)
    for rdn in ("dc=example,dc=com", "uid=admin", "cn=svc-webapp", "ou=people",
                "uid=jkowalski", "uid=aczarnecki", "ou=assets", "cn=serwer-vpn"):
        assert rdn in html
    # Pełny DN jest dostępny w podpowiedzi węzła.
    assert 'title="uid=jkowalski,ou=people,dc=example,dc=com"' in html
    assert "Jan Kowalski" in html


def test_directory_page_does_not_leak_secrets(client):
    html = client.get("/directory").get_data(as_text=True)
    assert "FLAG{" not in html
    assert "KEY-7731" not in html          # ukryty rekord z Zadania 3
    assert "Kowalski-Lab-101" not in html   # wartości userPassword
    assert "7429" not in html               # recoveryPin z Zadania 4


def test_directory_is_linked_in_nav(client):
    html = client.get("/").get_data(as_text=True)
    assert 'href="/directory"' in html


def test_no_task_solved_at_start(client):
    html = client.get("/").get_data(as_text=True)
    assert "Zaliczono 0 z 4." in html
    assert 'class="solved"' not in html
    assert "Zaliczone" not in html


def test_valid_flag_marks_task_solved(client):
    task = SCENARIOS[1]
    html = client.post("/flags", data={"flag": task.flag}).get_data(as_text=True)
    assert "Flaga poprawna" in html
    # Kafelek zadania w menu jest zielony (na każdej stronie)...
    assert f'class="solved" href="/{task.endpoint.split(".")[1]}"' in html
    # ...a na stronie głównej zadanie jest zaliczone, pozostałe nie.
    html = client.get("/").get_data(as_text=True)
    assert "Zaliczono 1 z 4." in html
    assert html.count("&#10003; Zaliczone") == 1
    assert html.count('class="solved"') == 1


def test_invalid_flag_does_not_mark_anything(client):
    html = client.post("/flags", data={"flag": "FLAG{zla_flaga}"}).get_data(as_text=True)
    assert "To nie jest prawidłowa flaga." in html
    assert "Zaliczono 0 z 4." in client.get("/").get_data(as_text=True)


def test_all_flags_solve_all_tasks(client):
    for s in SCENARIOS:
        client.post("/flags", data={"flag": s.flag})
    client.post("/flags", data={"flag": SCENARIOS[0].flag})   # ponowne wpisanie nie dubluje
    html = client.get("/").get_data(as_text=True)
    assert "Zaliczono 4 z 4." in html
    assert html.count('class="solved"') == len(SCENARIOS)


def test_congrats_and_confetti_after_last_flag(client):
    for s in SCENARIOS[:-1]:
        html = client.post("/flags", data={"flag": s.flag}).get_data(as_text=True)
        assert "CTF ukończony" not in html
        assert "confetti.js" not in html

    html = client.post("/flags", data={"flag": SCENARIOS[-1].flag}).get_data(as_text=True)
    assert "CTF ukończony" in html
    assert "confetti.js" in html

    # Gratulacje zostają na stronie głównej, ale konfetti już się nie powtarza.
    assert "CTF ukończony" in client.get("/").get_data(as_text=True)
    html = client.post("/flags", data={"flag": SCENARIOS[0].flag}).get_data(as_text=True)
    assert "CTF ukończony" in html
    assert "confetti.js" not in html


def test_confetti_script_is_served(client):
    assert client.get("/static/confetti.js").status_code == 200
