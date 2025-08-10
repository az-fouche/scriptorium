## Deployment Guide

This project includes a Flask webapp under `webapp/`. The production WSGI entrypoint is `webapp/wsgi.py` exposing `application`.

### Prerequisites
- SQLite database placed at `webapp/databases/books.db` (or set `DATABASE_PATH` env var)
- Python 3.11 (for local run) or Docker (for containerized deploy)

### Environment Variables
- `SECRET_KEY`: A secure random string
- `FLASK_DEBUG`: `false` in production
- `DATABASE_PATH`: Absolute path to your SQLite database if not using the default
- `FLASK_HOST`, `FLASK_PORT`: Optional network config

### Run Locally (production style)
```
pip install -r webapp/requirements.txt
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
gunicorn webapp.wsgi:application --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 120
```

### Docker
Build and run:
```
docker build -t library-webapp .
docker run --rm -p 5000:5000 \
  -e SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") \
  -e FLASK_DEBUG=false \
  -v %CD%/webapp/databases:/app/webapp/databases \
  library-webapp
```
On Linux/macOS replace the bind mount path with $(pwd).

### Render
- New Web Service → Connect repo
- Build Command: `pip install -r webapp/requirements.txt`
- Start Command: `gunicorn webapp.wsgi:application --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 120`
- Environment: `PYTHON_VERSION=3.11.x`; add `SECRET_KEY`, optional `DATABASE_PATH`
- Persist/Upload `webapp/databases/books.db` via a Persistent Disk or prebundle it

### Railway
- New Service from Repo
- Install Command: `pip install -r webapp/requirements.txt`
- Start Command: same as above
- Add variables: `SECRET_KEY`, optional `DATABASE_PATH`
- Mount a volume at `/app/webapp/databases` or bake DB into the image

### Heroku (Container or Buildpack)
- Using this repo’s `Procfile`:
  - heroku create
  - heroku buildpacks:add heroku/python
  - git push heroku main
  - heroku config:set SECRET_KEY=...
  - heroku config:set FLASK_DEBUG=false
  - Upload `books.db` to an attached storage or bake it into the slug

### Database notes
- Default DB path is `webapp/databases/books.db`. To use an external DB file, set `DATABASE_PATH` env var to an absolute path.
- The production config disables the auto-reloader that scans the DB file for changes.

### Health checks
You can use `/api/test-database` and `/api/debug-database` while `DEBUG=true`. Disable in production by keeping `FLASK_DEBUG=false`.


