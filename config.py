import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'irctc-secret-key-antigravity-2026-super-secure')

    # Render sets DATABASE_URL for Postgres; for free tier we stick with SQLite
    _db_url = os.environ.get('DATABASE_URL', 'sqlite:///trainapp.db')
    # Render Postgres URLs start with postgres:// but SQLAlchemy needs postgresql://
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Render provides the PORT env var
    PORT = int(os.environ.get('PORT', 5000))
