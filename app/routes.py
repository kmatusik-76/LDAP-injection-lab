from flask import (
    Blueprint, current_app, redirect, render_template, request, session, url_for,
)

from .ldap_filter import FilterError, describe, parse_filter
from .scenarios import ALL_FLAGS, SCENARIOS, SCENARIOS_BY_ENDPOINT

bp = Blueprint("main", __name__)


def _explain_filter(ldap_filter):
    """Zwraca czytelny opis drzewa filtra albo None, gdy filtr jest bledny."""
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
    return redirect(request.referrer or url_for("main.index"))


@bp.route("/")
def index():
    return render_template("index.html")


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
        field_label="Szukaj po nazwisku, mailu lub loginie",
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


@bp.route("/console")
def console():
    ldap_filter = request.args.get("filter")
    result = app_logic().console_query(ldap_filter) if ldap_filter else None
    return render_template(
        "console.html",
        result=result,
        ldap_filter=ldap_filter or "",
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
