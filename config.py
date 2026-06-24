import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Secret key for session security
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-fallback-secret-key-12345')
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///wellness.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask Environment
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'
