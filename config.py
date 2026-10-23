import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
basedir = Path(__file__).resolve().parent
load_dotenv(basedir / '.env')

class Config:
    # Flask Secret Key
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # MySQL connection parameters (loaded strictly from environment variables)
    MYSQL_HOST = os.getenv('MYSQL_HOST')
    MYSQL_USER = os.getenv('MYSQL_USER')
    MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')
    MYSQL_SSL_DISABLED = os.getenv('MYSQL_SSL_DISABLED', 'False').lower() in ('true', '1')

    # Resolve database URL
    _db_url = os.getenv('DATABASE_URL')

    if not _db_url:
        if MYSQL_HOST and MYSQL_USER and MYSQL_PASSWORD and MYSQL_DATABASE:
            ssl_param = 'True' if MYSQL_SSL_DISABLED else 'False'
            _db_url = (
                f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
                f"?ssl_disabled={ssl_param}"
            )
        else:
            # Safe local fallback when no MySQL credentials are configured
            _db_url = 'sqlite:///trainapp.db'

    # Normalize driver prefixes for SQLAlchemy compatibility
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    elif _db_url.startswith('mysql://'):
        _db_url = _db_url.replace('mysql://', 'mysql+mysqlconnector://', 1)

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }

    # Render / web server port configuration
    PORT = int(os.getenv('PORT', 5000))
