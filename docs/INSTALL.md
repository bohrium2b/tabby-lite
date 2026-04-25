Install and Docker Compose guide
===============================

This guide shows a minimal Docker Compose setup for running tabby-lite with PostgreSQL and Redis. It also shows how to optionally include a Tabbycat service. You can share the PostgreSQL instance between tabby-lite and Tabbycat, but only do this if you understand the Tabbycat schema and potential conflicts.

Prerequisites
-------------
- Docker and Docker Compose (or Docker Compose v2 plugin) installed on the host
- (Optional) Basic familiarity with environment variables and Docker networking

Example docker-compose.yml
--------------------------
Below is a minimal example you can save as `docker-compose.yml`. Adjust usernames, passwords, and image tags as needed.

```yaml
version: "3.9"

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: tabby
      POSTGRES_PASSWORD: tabby_pass
      POSTGRES_DB: tabbylite
    volumes:
      - db_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    command: ["redis-server", "--save", "", "--appendonly", "no"]

  # Optional: Tabbycat service (if you want to run Tabbycat locally).
  # Many users run Tabbycat separately; include here only if you have a Tabbycat image/config.
  # tabbycat:
  #   image: <tabbycat-image>
  #   environment:
  #     DATABASE_URL: postgres://tabby:tabby_pass@db:5432/tabbycat_db
  #   depends_on:
  #     - db

  web:
    build: .
    depends_on:
      - db
      - redis
    environment:
      DJANGO_SECRET_KEY: changeme_secure_key
      DEBUG: 'False'
      DATABASE_URL: postgres://tabby:tabby_pass@db:5432/tabbylite
      REDIS_URL: redis://redis:6379/0
      DJANGO_USE_REDIS: 'true'
      # If you have a Tabbycat instance, point to it (optional):
      # TABBY_HOST: 'http://tabbycat:8000'
      # TABBY_TOURNAMENT: 'my-tournament'
      # TABBY_AUTHENTICATION_TOKEN: ''
    ports:
      - "8000:80"
    volumes:
      - static_volume:/home/app/web/static
    command: /bin/bash -c "python manage.py migrate --noinput && python manage.py collectstatic --noinput && /sbin/my_init"

volumes:
  db_data:
  static_volume:

networks:
  default:
    name: tabbylite_net

```

Notes on sharing Postgres with Tabbycat
--------------------------------------
- It's possible to point both Tabbycat and tabby-lite to the same PostgreSQL server instance. However, sharing a single database (same DB name) between two different applications may cause schema conflicts. If you want to share the same Postgres server, use separate database names (e.g., `tabbycat_db` and `tabbylite`) and separate DB users.

Startup and first-run
---------------------
Start services:

```bash
docker compose up -d --build
```

Check logs (optional):

```bash
docker compose logs -f web
```

Creating an admin user
----------------------
If the `web` service's `command` runs migrations and then starts, you can create a superuser by running:

```bash
docker compose exec web python manage.py createsuperuser
```

Background tasks (Celery)
-------------------------
The example `Dockerfile` sets up service scripts for Celery worker and beat when using the Phusion Passenger image; if you prefer a Docker-native approach, consider running Celery in a separate container:

```yaml
  worker:
    build: .
    command: celery -A tabby_lite worker -l info
    depends_on:
      - redis
      - db

  beat:
    build: .
    command: celery -A tabby_lite beat -l info
    depends_on:
      - redis
      - db
```

Environment variables reference
-------------------------------
- `DATABASE_URL` — Postgres connection URL, e.g. `postgres://user:pass@db:5432/dbname`
- `REDIS_URL` — Redis connection, e.g. `redis://redis:6379/0`
- `TABBY_HOST` — URL for Tabbycat tournament instance (optional)
- `TABBY_TOURNAMENT` — Tournament slug/name used by Tabbycat (optional)
- `TABBY_AUTHENTICATION_TOKEN` — If Tabbycat API requires a token (optional)
- `DJANGO_SECRET_KEY` — Django secret key (set to a strong value in production)

Troubleshooting
---------------
- If migrations fail, inspect `docker compose logs web` and ensure the DB is reachable and credentials match.
- If Celery cannot connect to Redis, verify `REDIS_URL` and that the `redis` service is healthy.

Further notes
-------------
See the repository `Dockerfile` and `docker-compose.example.yml` for an existing example setup. If you want, I can create a ready-to-run `docker-compose.yml` tailored to your environment or add a Makefile to simplify common tasks.
