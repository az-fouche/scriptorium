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



## OVH (Ubuntu 22.04) — Quick Deploy with Docker Compose

1) SSH to the server
```
ssh ubuntu@YOUR_SERVER_IP
```

2) Check and configure firewall (UFW)
```
sudo ufw status
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```
Also verify OVH network-level firewall in the OVH Manager (Network → IP → Your IP → Firewall) is disabled or allows TCP 22/80/443.

3) Install Docker Engine and Compose plugin
```
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
docker --version && docker compose version
```

4) Pull project and prepare env
```
git clone <your-repo-url> /opt/library-webapp
cd /opt/library-webapp
cp .env.example .env
# Generate a secure key
python3 -c "import secrets; print(secrets.token_hex(32))" | sed 's/.*/SECRET_KEY=&/' | tee -a .env
# Optionally set external DB path when ready (absolute path on server)
# echo DATABASE_PATH=/app/webapp/databases/books.db >> .env
```

5) First run (HTTP on port 80)
```
docker compose up -d --build
docker compose logs -f
```
Open http://YOUR_SERVER_IP in a browser.

6) Replace the database later
- Copy your `books.db` to the host path mapped in `docker-compose.yml` (default `webapp/databases/books.db`). For example:
```
scp path/to/books.db ubuntu@YOUR_SERVER_IP:/opt/library-webapp/webapp/databases/books.db
```
- Then restart the container:
```
cd /opt/library-webapp && docker compose restart
```

7) Enable HTTPS later (domain ready)
- Add a reverse proxy (Caddy or Nginx+Certbot). For Caddy (recommended, simplest auto-HTTPS): install Caddy and proxy `:443` to `web:5000` with your domain. A sample `Caddyfile` can be added on request.
