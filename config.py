"""
Configuration module for Feed Comparator application.
Loads settings from environment variables with sensible defaults.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class."""
    
    # Flask secret key - MUST be set in production!
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production-WARNING')
    
    # Security: Allowed domains for XML feed URLs (comma-separated)
    # Leave empty to allow all domains (not recommended for production)
    ALLOWED_DOMAINS = [d.strip() for d in os.getenv('ALLOWED_DOMAINS', '').split(',') if d.strip()]
    
    # Maximum XML file size in bytes (default: 10MB)
    MAX_XML_SIZE = int(os.getenv('MAX_XML_SIZE', 10485760))
    
    # Request timeout in seconds for fetching XML feeds
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))
    
    # Flask environment (development/production)
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    # Debug mode (should be False in production)
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
    
    # Port for Flask application
    PORT = int(os.getenv('PORT', 5001))
    
    @classmethod
    def validate(cls):
        """Validate critical configuration settings."""
        warnings = []
        
        if cls.SECRET_KEY == 'dev-key-change-in-production-WARNING':
            warnings.append("WARNING: Using default SECRET_KEY! Set SECRET_KEY in .env file for production!")
        
        if cls.FLASK_ENV == 'production' and cls.DEBUG:
            warnings.append("WARNING: DEBUG mode is enabled in production!")
        
        if not cls.ALLOWED_DOMAINS and cls.FLASK_ENV == 'production':
            warnings.append("INFO: ALLOWED_DOMAINS not set - all domains will be accepted")
        
        return warnings

