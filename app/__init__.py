import os
from flask import Flask

from .ldap_client import LdapClient

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "laboratorium-ldapi-klucz-dev")
    app.config["LDAP_CLIENT"] = LdapClient()
    from .routes import bp
    app.register_blueprint(bp)
    return app