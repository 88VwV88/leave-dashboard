from flask import Flask, redirect, url_for
from database import init_app_database

from routes.dashboard import router as dashboard

# Ensure models are imported for Flask-Migrate to detect them
import models  # noqa: F401
from models import User, Role

from database import db

from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))
app.config.from_object("config.AppConfig")

init_app_database(app)
app.migrate = Migrate(app, db)

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
app.security = Security(app, user_datastore)

app.register_blueprint(dashboard)


@app.route("/")
def index():
    return redirect(url_for("dashboard.home"))


@app.route("/health-check")
def health_check():
    return {"status": "OK"}


if __name__ == "__main__":
    with app.app_context():
        import flask_security

        # Seed roles
        admin_role = user_datastore.find_or_create_role(
            name="admin", description="Administrator"
        )
        maintainer_role = user_datastore.find_or_create_role(
            name="maintainer", description="Maintainer"
        )
        db.session.commit()

        # Seed admin user
        admin_email = os.environ.get("ADMIN_EMAIL")
        if admin_email and not user_datastore.find_user(email=admin_email):
            admin_user = user_datastore.create_user(
                email=admin_email,
                password=flask_security.hash_password(os.environ.get("ADMIN_PASSWORD")),
            )
            user_datastore.add_role_to_user(admin_user, admin_role)
            db.session.commit()

        # Seed maintainer user
        maintainer_email = os.environ.get("MAINTAINER_EMAIL")
        if maintainer_email and not user_datastore.find_user(email=maintainer_email):
            maintainer_user = user_datastore.create_user(
                email=maintainer_email,
                password=flask_security.hash_password(
                    os.environ.get("MAINTAINER_PASSWORD")
                ),
            )
            user_datastore.add_role_to_user(maintainer_user, maintainer_role)
            db.session.commit()
