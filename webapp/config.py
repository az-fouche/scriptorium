import os
from pathlib import Path

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database configuration
    BASE_DIR = Path(__file__).parent.parent
    # Allow overriding DB path via env var; fallback to bundled path
    _ENV_DB = os.environ.get('DATABASE_PATH')
    DATABASE_PATH = Path(_ENV_DB) if _ENV_DB else (BASE_DIR / 'webapp' / 'databases' / 'books.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    
    # App configuration
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 5000))
    
    # Database reload configuration
    DB_RELOAD_CHECK_INTERVAL = 5  # seconds
    DB_RELOAD_ENABLED = True

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    DB_RELOAD_ENABLED = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    DB_RELOAD_ENABLED = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
