import os

from flask import Flask

from .services import LdapApp


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "laboratorium-ldap-klucz-dev")
    app.config["LDAP_APP"] = LdapApp()

    from .routes import bp
    app.register_blueprint(bp)
    return app
