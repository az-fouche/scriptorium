"""
Flask extensions and middleware for the library webapp
"""

import os
import time
from datetime import datetime
from typing import Optional
from flask import Flask, current_app
from sqlalchemy import create_engine, text as sql_text
from flask_session import Session

try:
    from .models import db
except ImportError:
    from models import db


class DatabaseReloader:
    """Database auto-reload mechanism"""
    
    def __init__(self, db_path: str = None, check_interval: int = None):
        if db_path is None:
            db_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), '..', 'databases', 'subset_books.db'
            ))
        self.db_path = db_path
        self.last_modified = self._get_db_mtime()
        self.last_check = time.time()
        # Check every N seconds (default 5)
        if check_interval is None:
            try:
                check_interval = int(os.environ.get('DB_RELOAD_CHECK_INTERVAL', '5'))
            except Exception:
                check_interval = 5
        self.check_interval = int(check_interval)
    
    def _get_db_mtime(self) -> float:
        """Get database file modification time"""
        try:
            return os.path.getmtime(self.db_path)
        except OSError:
            return 0
    
    def should_reload(self) -> bool:
        """Check if database should be reloaded"""
        current_time = time.time()
        
        # Only check every few seconds to avoid excessive file system calls
        if current_time - self.last_check < self.check_interval:
            return False
        
        self.last_check = current_time
        current_mtime = self._get_db_mtime()
        
        if current_mtime > self.last_modified:
            self.last_modified = current_mtime
            return True
        
        return False
    
    def reload_database(self) -> bool:
        """Reload database connection"""
        try:
            # Close existing connections
            db.session.close()
            db.engine.dispose()
            
            # Recreate engine and session using the proper SQLAlchemy method
            new_engine = create_engine(current_app.config['SQLALCHEMY_DATABASE_URI'])
            db.session = db.create_scoped_session(new_engine)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Database reloaded successfully")
            return True
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Database reload failed: {e}")
            return False


def init_extensions(app: Flask):
    """Initialize Flask extensions"""
    # Initialize SQLAlchemy
    db.init_app(app)
    # Ensure helpful indexes exist (idempotent for SQLite)
    try:
        with app.app_context():
            conn = db.engine.connect()
            conn.execute(sql_text("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)"))
            conn.execute(sql_text("CREATE INDEX IF NOT EXISTS idx_books_authors ON books(authors)"))
            conn.execute(sql_text("CREATE INDEX IF NOT EXISTS idx_books_primary_genre ON books(primary_genre)"))
            conn.execute(sql_text("CREATE INDEX IF NOT EXISTS idx_books_language ON books(language)"))
            conn.execute(sql_text("CREATE INDEX IF NOT EXISTS idx_books_created_at ON books(created_at)"))
            conn.close()
    except Exception:
        # Non-fatal: continue without indexes if creation fails
        pass
    
    # Initialize Flask-Session
    Session(app)
    
    # Initialize database reloader if enabled
    if app.config.get('DB_RELOAD_ENABLED', True):
        # Ensure the reloader watches the active DB path from config
        db_reloader = DatabaseReloader(
            db_path=str(app.config.get('DATABASE_PATH')),
            check_interval=int(app.config.get('DB_RELOAD_CHECK_INTERVAL', 5))
        )
        app.db_reloader = db_reloader
        
        # Register before_request handler
        @app.before_request
        def check_database_updates():
            """Check if database has been updated and reload if necessary"""
            if db_reloader.should_reload():
                db_reloader.reload_database()
    
    return app
