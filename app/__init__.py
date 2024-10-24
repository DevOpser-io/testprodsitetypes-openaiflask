from flask import Flask
from config import Config
from pathlib import Path
from flask_session import Session
import redis
import logging

APP_ROOT_PATH = Path(__file__).parent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_old_cache(app):
    redis_client = app.config['REDIS_CLIENT']
    current_version = app.config['CACHE_VERSION']
    try:
        for key in redis_client.scan_iter("chat:*"):
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            if not key.startswith(f"chat:{current_version}:"):
                redis_client.delete(key)
        for key in redis_client.scan_iter("session:*"):
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            if not key.startswith(f"session:{current_version}:"):
                redis_client.delete(key)
        logger.info(f"Old cache cleared for version {current_version}")
    except redis.RedisError as e:
        logger.error(f"Redis error when clearing old cache: {str(e)}")

def create_app():
    """Initialize the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)
    app.secret_key = app.config['FLASK_SECRET_KEY']

    # Initialize session
    server_session = Session(app)

    # Initialize Redis client
    app.config['REDIS_CLIENT'] = redis.from_url(app.config['REDIS_URL'])

    with app.app_context():
        from . import routes
        
        # Clear old cache on startup
        clear_old_cache(app)
        
        logger.info(f"Application started with CACHE_VERSION: {app.config['CACHE_VERSION']}")
        
        return app