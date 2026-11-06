from __future__ import annotations

import re

from flask import (
    Blueprint, current_app, redirect, render_template, request, session, url_for,
)
from markupsafe import Markup, escape

from .dit import build_tree
from .ldap_filter import FilterError, describe, parse_filter
from .scenarios import ALL_FLAGS, SCENARIOS, SCENARIOS_BY_ENDPOINT

bp = Blueprint("main", __name__)


def _explain_filter(ldap_filter):
    """Zwraca czytelny opis drzewa filtra albo None, gdy filtr jest błędny."""
    if not ldap_filter:
        return None
    try:
        return describe(parse_filter(ldap_filter))
    except FilterError:
        return None


def app_logic():
    return current_app.config["LDAP_APP"]


def is_secure() -> bool:
    return bool(session.get("secure", False))


def _local_path(target: str | None) -> str:
    """Pilnuje, żeby przełącznik trybu wracał tylko na adresy tej aplikacji."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("main.index")


_INLINE_CODE = re.compile(r"`([^`]+)`")


@bp.app_template_filter("inline_code")
def inline_code(text: str) -> Markup:
    """Zamienia `fragmenty` w opisach zadań na <code>. Najpierw escapuje całość,
    więc treść nie może wstrzyknąć własnego HTML-a."""
    return Markup(_INLINE_CODE.sub(r"<code>\1</code>", str(escape(text))))


@bp.app_context_processor
def inject_globals():
    return {
        "secure_mode": is_secure(),
        "scenarios": SCENARIOS,
        "explain_filter": _explain_filter,
    }


@bp.route("/toggle", methods=["POST"])
def toggle():
    session["secure"] = not is_secure()
    # Wracamy na tę samą stronę (z zapytaniem), żeby od razu było widać,
    # jak ten sam atak zachowuje się w drugim trybie.
    return redirect(_local_path(request.form.get("next")))


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/directory")
def directory():
    tree = build_tree(app_logic().server.entries)
    return render_template("directory.html", tree=tree)


@bp.route("/login", methods=["GET", "POST"])
def login():
    result = None
    if request.method == "POST":
        result = app_logic().login(
            request.form.get("username", ""),
            request.form.get("password", ""),
            secure=is_secure(),
        )
    return render_template(
        "task.html",
        scenario=SCENARIOS_BY_ENDPOINT["main.login"],
        template_name="form_login.html",
        result=result,
    )


@bp.route("/people")
def people():
    query = request.args.get("q")
    result = app_logic().people_search(query, is_secure()) if query is not None else None
    return render_template(
        "task.html",
        scenario=SCENARIOS_BY_ENDPOINT["main.people"],
        template_name="form_search.html",
        result=result,
        query=query or "",
        field_label="Szukaj po imieniu i nazwisku (cn), adresie e-mail lub loginie",
        search_endpoint="main.people",
    )


@bp.route("/assets")
def assets():
    query = request.args.get("q")
    result = app_logic().asset_search(query, is_secure()) if query is not None else None
    return render_template(
        "task.html",
        scenario=SCENARIOS_BY_ENDPOINT["main.assets"],
        template_name="form_search.html",
        result=result,
        query=query or "",
        field_label="Szukaj zasobu po nazwie (cn) lub dziale (ou)",
        search_endpoint="main.assets",
    )


@bp.route("/recovery", methods=["GET", "POST"])
def recovery():
    result = None
    uid = "aczarnecki"
    pin = ""
    if request.method == "POST":
        uid = request.form.get("uid", "")
        pin = request.form.get("pin", "")
        result = app_logic().recovery(uid, pin, secure=is_secure())
    return render_template(
        "task.html",
        scenario=SCENARIOS_BY_ENDPOINT["main.recovery"],
        template_name="form_recovery.html",
        result=result,
        uid=uid,
        pin=pin,
    )


@bp.route("/flags", methods=["GET", "POST"])
def flags():
    checked = None
    value = ""
    if request.method == "POST":
        value = request.form.get("flag", "").strip()
        checked = {
            "value": value,
            "valid": value in ALL_FLAGS,
            "title": ALL_FLAGS.get(value),
        }
    return render_template("flags.html", checked=checked, value=value)
