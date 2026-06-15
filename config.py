import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI", "sqlite:///tasks.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False