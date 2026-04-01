import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class AppConfig:
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SQLALCHEMY_DATABASE_URI", "postgresql://user:password@localhost:5432/leavedb"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = os.environ.get(
        "SQLALCHEMY_TRACK_MODIFICATIONS", "False"
    ).lower() in ("true", "1", "t")
    SQLALCHEMY_ECHO = os.environ.get("SQLALCHEMY_ECHO", "True").lower() in (
        "true",
        "1",
        "t",
    )
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "f0cbcc37a095dd28bb5574685bd8faf457dc68f68fa3ec4c303dc2864ca9da55"
    )
    SECURITY_PASSWORD_SALT = os.environ.get(
        "SECURITY_PASSWORD_SALT", "e64f89d38c64224090fc2185bf2d23be"
    )
    SECURITY_PASSWORD_HASH = os.environ.get("SECURITY_PASSWORD_HASH", "bcrypt")
    SECURITY_LOGIN_URL = os.environ.get("SECURITY_LOGIN_URL", "/login")
    SECURITY_POST_LOGIN_VIEW = os.environ.get("SECURITY_POST_LOGIN_VIEW", "/dashboard/")
    SECURITY_REGISTERABLE = os.environ.get(
        "SECURITY_REGISTERABLE", "False"
    ).lower() in ("true", "1", "t")
    SECURITY_SEND_REGISTER_EMAIL = os.environ.get(
        "SECURITY_SEND_REGISTER_EMAIL", "False"
    ).lower() in ("true", "1", "t")
    SECURITY_VIEW_CONTAINER = os.environ.get("SECURITY_VIEW_CONTAINER", "security")
