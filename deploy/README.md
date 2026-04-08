# Deploy with Phusion Passenger (Docker)

This directory contains a sample Nginx/Passenger configuration and the WSGI startup file used to run this Django app under Phusion Passenger inside Docker.

Files added:

- `../passenger_wsgi.py` — WSGI entrypoint Passenger will load (placed at repository root).
- `nginx.passenger.conf` — sample Nginx server block configured for Passenger.

Quick notes / example workflow

1. Build an image with Passenger + Nginx and Python installed and copy the project into the container at `/home/app/web`.
2. Ensure `passenger_wsgi.py` is at `/home/app/web/passenger_wsgi.py` inside the container.
3. Install project dependencies and run `python manage.py collectstatic --noinput` so static files live in `/home/app/web/static`.
4. Place `nginx.passenger.conf` in the container's Nginx sites-enabled (for example `/etc/nginx/sites-enabled/app.conf`).

Minimal Dockerfile snippet (example, adapt to your base image):

```dockerfile
# FROM <an image with passenger + nginx + python installed>
# COPY . /home/app/web
# WORKDIR /home/app/web
# RUN pip install -r requirements.txt
# RUN python manage.py collectstatic --noinput
# COPY deploy/nginx.passenger.conf /etc/nginx/sites-enabled/app.conf
# EXPOSE 80
# CMD ["/usr/sbin/nginx", "-g", "daemon off;"]
```

Notes:
- Adjust `root`/`alias` paths in `nginx.passenger.conf` to where your app is installed in the image.
- Optionally set `passenger_python` to the full Python interpreter path inside the image.
- Keep `DEBUG=False` and provide production secrets via environment variables.
