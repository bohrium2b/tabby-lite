# Example Dockerfile that runs this Django app with Phusion Passenger + Nginx.
#
# Notes:
# - This uses the official Phusion Passenger full image which includes Nginx + Passenger.
# - Adjust Python version, dependency install commands, and paths to match your environment.
# - You may prefer to build a slimmer image and install only the packages you need.

FROM phusion/passenger-full:latest

ENV HOME=/root
WORKDIR /home/app/web

# Copy application code
COPY . /home/app/web

# Install system deps, build deps for psycopg2 and Poetry
RUN apt-get update -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       python3 python3-venv python3-pip build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Create Venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Celery app module used by service scripts. Adjust if your app name differs.
ENV CELERY_APP=tabby_lite

# Install dependencies
RUN /opt/venv/bin/pip install --upgrade pip setuptools wheel && /opt/venv/bin/pip install -e .

# Collect static files using the venv python (explicit path avoids wrong python)
RUN /opt/venv/bin/python manage.py collectstatic --noinput || true

# Set passenger python path
ENV passenger_python=/opt/venv/bin/python
# Ensure Nginx sites-enabled and copy our sample Passenger config
RUN mkdir -p /etc/nginx/sites-enabled
# Remove Nginx default site
RUN rm -f /etc/nginx/sites-available/default
COPY deploy/nginx.passenger.conf /etc/nginx/sites-enabled/default
# Enable all write on the logs directory
RUN chmod 777 -R /home/app/web/logs
# Enable all write on the cache directory
RUN mkdir /home/app/web/cache
RUN chmod 777 -R /home/app/web/cache
# Enable nginx
RUN rm -f /etc/service/nginx/down
# Small services
RUN apt-get update -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /etc/service/celery-worker /etc/service/celery-beat /etc/service/cron \
    && printf '%s\n' '#!/bin/sh' 'if [ "${LIGHT_MEMORY_MODE}" = "True" ]; then echo "LIGHT_MEMORY_MODE=True, not starting celery worker"; exit 0; fi' 'exec /opt/venv/bin/celery -A "${CELERY_APP}" worker -c 1 --loglevel=INFO' > /etc/service/celery-worker/run \
    && chmod +x /etc/service/celery-worker/run \
    && printf '%s\n' '#!/bin/sh' 'if [ "${LIGHT_MEMORY_MODE}" = "True" ]; then echo "LIGHT_MEMORY_MODE=True, not starting celery beat"; exit 0; fi' 'exec /opt/venv/bin/celery -A "${CELERY_APP}" beat --loglevel=INFO' > /etc/service/celery-beat/run \
    && chmod +x /etc/service/celery-beat/run
# Ensure nginx has an explicit runit service that launches nginx in foreground
RUN mkdir -p /etc/service/nginx \
    && printf '%s\n' '#!/bin/sh' 'echo "Starting Nginx..." && exec /usr/sbin/nginx -g "daemon off;"' > /etc/service/nginx/run \
    && chmod +x /etc/service/nginx/run

# Pre-start commands
RUN mkdir -p /etc/my_init.d \ 
    && printf '%s\n' '#!/bin/sh' 'echo "Running pre-start commands..."' > /etc/my_init.d/00-pre-start.sh \
    && chmod +x /etc/my_init.d/00-pre-start.sh
# If LIGHT_MEMORY_MODE=True, create "down" files for celery services before runit starts
RUN printf '%s\n' '#!/bin/sh' 'if [ "${LIGHT_MEMORY_MODE}" = "True" ]; then' '  echo "LIGHT_MEMORY_MODE=True: disabling celery services"' '  touch /etc/service/celery-worker/down' '  touch /etc/service/celery-beat/down' 'fi' > /etc/my_init.d/00-disable-celery-if-light-memory.sh \
    && chmod +x /etc/my_init.d/00-disable-celery-if-light-memory.sh

# Configure nginx at container start to bind to Railway's $PORT (if provided)
RUN cat > /etc/my_init.d/05-configure-nginx-port.sh <<'SH'
#!/bin/sh
set -e
echo "Configuring nginx for runtime port $PORT"

# Replace listen 80 with the PORT env if provided
if [ -n "$PORT" ]; then
    sed -i "s/listen 80;/listen ${PORT};/g" /etc/nginx/sites-enabled/default || true
fi

# Ensure passenger_python is set in config (fallback if missing)
if ! grep -q "passenger_python" /etc/nginx/sites-enabled/default; then
    sed -i '/passenger_startup_file/a\    passenger_python /opt/venv/bin/python;' /etc/nginx/sites-enabled/default || true
fi

exit 0
SH
        && chmod +x /etc/my_init.d/05-configure-nginx-port.sh
# Database migration pre-start task
RUN printf '%s\n' '#!/bin/sh' 'echo "Running database migration..." && /opt/venv/bin/python manage.py migrate' > /etc/my_init.d/01-migrate.sh \
    && chmod +x /etc/my_init.d/01-migrate.sh
# Static files pre-start task
RUN printf '%s\n' '#!/bin/sh' 'echo "Running static files collection..." && /opt/venv/bin/python manage.py collectstatic --noinput || true' > /etc/my_init.d/02-collectstatic.sh \
    && chmod +x /etc/my_init.d/02-collectstatic.sh


EXPOSE 80

# Start container with Phusion's init which will run Nginx + Passenger

CMD ["/sbin/my_init"]

