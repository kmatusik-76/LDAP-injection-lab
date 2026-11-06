from flask import (
    Blueprint, current_app, redirect, render_template,
    request, session, url_for,
)

bp = Blueprint("main", __name__)

def client():
    return current_app.config["LDAP_CLIENT"]

def is_secure() -> bool:
    return bool(session.get("secure", False))

@bp.app_context_processor
def inject_mode():
    return {"secure_mode" : is_secure(), "current_user": session.get("user")}

@bp.route("/")
def index():
    return redirect(url_for("main.login"))

@bp.route("/toggle", methods=["POST"])
def toggle():
    session["secure"] = not is_secure()
    return redirect(request.referrer or url_for("main.login"))

@bp.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return redirect(url_for("main.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    result = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        result = client().authenticate(username, password, secure=is_secure())
        if result.ok:
            session["user"] = result.entries[0]
            return redirect(url_for("main.search"))
    return render_template("login.html", result=result)


@bp.route("/search")
def search():
    query = request.args.get("q")
    result = client().search_people(query, secure=is_secure()) if query is not None else None
    return render_template("search.html", result=result, query=query or "")
