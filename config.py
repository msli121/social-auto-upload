from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    PORT = 10001
    SECRET_KEY = 'your_secret_key_here'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_TO_STDOUT = True

class DevelopmentConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/dev_db'

class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/test_db'

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/prod_db'