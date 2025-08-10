"""
WSGI entrypoint for production servers.

Exposes `application` for WSGI servers like Gunicorn/Waitress.
"""

from .app_refactored import create_app

# Use production config by default in WSGI context
application = create_app('production')

# Optional: allow `python -m webapp.wsgi` to run locally
if __name__ == '__main__':
    application.run(host=application.config.get('HOST', '0.0.0.0'),
                    port=application.config.get('PORT', 5000))


