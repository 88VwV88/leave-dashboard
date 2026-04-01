from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.orm import DeclarativeBase


class BaseModel(DeclarativeBase): ...  # BaseModel for SQL models


db = SQLAlchemy(model_class=BaseModel)


def init_app_database(app: Flask):
    db.init_app(app)
