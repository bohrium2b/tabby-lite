# tabby-lite

A lightweight wrapper on Tabbycat for running small tournaments and simplifying the workflow for small events.

Purpose
-------
tabby-lite provides a small, opinionated Django application that integrates with a Tabbycat tournament instance to simplify tournament management for smaller events. It focuses on lightweight deployment and easy integration with an existing Tabbycat server.

User Features
-------------
- Fetches rounds, draws and tournament data from a Tabbycat API and displays them in the UI
- Round draw display with manual refresh (cache invalidation) and venue lookup
- Team-facing draw CSV export for notifying teams (includes speaker emails and sides)
- Adjudicator draw CSV export including confidential passphrases (for emailing adjudicators)
- Team registration form that creates teams and speakers via the Tabbycat API (optimistic PendingSubmission + background sync)
- Ballot submission using private passphrases: per-pairing passphrase generation and passphrase-protected ballot forms
- Optimistic local state and duplicate-prevention for ballot submissions (marks ballots completed locally)
- Background sync of queued submissions to Tabbycat via Celery tasks
- Passphrase generation utility with configurable formats (wordlists + letters/numbers)
- BYE handling and simple export-friendly formatting for draws

Architecture Overview
---------------------
- The project is a Django application with Celery for background processing. Static files are collected with `collectstatic` and served via Whitenoise (or an external web server when deployed behind Nginx/Passenger).
- Configuration is environment-driven (12-factor), commonly using `DATABASE_URL`, `REDIS_URL`, and `DJANGO_SECRET_KEY`.
- Tabbycat integration is optional — tabby-lite talks to a separate Tabbycat instance over its API. It can share the same PostgreSQL database as Tabbycat if desired, but sharing databases should be done carefully.

Quick Start
-----------
For a step-by-step Docker Compose installation and a sample `docker-compose.yml` that brings up PostgreSQL, Redis, and tabby-lite (and optionally a Tabbycat instance), see the installation guide: [docs/INSTALL.md](docs/INSTALL.md)

Development notes
-----------------
- Entry point: `manage.py` (Django settings module: `tabby_lite.settings`)
- Main Django app lives under the project package `tabby_lite/` and related apps such as `account/`.
- Dependencies are listed in `pyproject.toml` and include: `django`, `django-vite`, `djangorestframework`, `celery`, `django-redis`, `psycopg2-binary`, `gunicorn`, and others.

Files of interest
-----------------
- [pyproject.toml](pyproject.toml) — Python package metadata and dependencies
- [Dockerfile](Dockerfile) — example Dockerfile using Phusion Passenger + Nginx
- [docker-compose.example.yml](docker-compose.example.yml) — example compose fragment showing `web` service
- [manage.py](manage.py) — Django CLI entrypoint

Contributing
------------
See the code and open issues or pull requests. 

Licensing
------------
This code is licensed under a MIT license. You are free to use, copy, modify, merge, publish, distribute, sublicense, and sell this software for commercial or non-commercial uses. Please don't expect support from me if you are making your own modifications in closed-source. I don't have time.
