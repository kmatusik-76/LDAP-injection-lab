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
    for label in ("Cel:", "Dowód wykonania:", "Na czym polega luka",
                  "Podpowiedź", "Co zmienia tryb BEZPIECZNY"):
        assert label in html


def test_index_lists_all_tasks(client):
    html = client.get("/").get_data(as_text=True)
    for s in SCENARIOS:
        assert s.title in html


def test_inline_code_is_rendered_and_escaped(client):
    html = client.get("/login").get_data(as_text=True)
    # Fragment w `...` staje się <code>, a znaki specjalne są escapowane.
    assert "<code>(&amp;(uid=TWÓJ_LOGIN)(userPassword=TWOJE_HASŁO))</code>" in html
