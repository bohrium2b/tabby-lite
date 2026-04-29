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
RUN mkdir -p /home/app/web/cache
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
RUN mkdir -p /etc/service/nginxng \
        && cat > /etc/service/nginxng/run <<'SH'
#!/bin/sh
set -e

if pgrep -x nginx >/dev/null 2>&1; then
    echo "Nginx is already running; not starting another instance."
    exec sleep infinity
fi
echo "Starting Nginx..."
# If the main nginx config already contains a 'daemon' directive, avoid passing -g to prevent duplicate directive errors.
if grep -Eiq '^\s*daemon\b' /etc/nginx/nginx.conf 2>/dev/null; then
    echo "Detected 'daemon' in nginx.conf; starting nginx without -g"
    exec /usr/sbin/nginx
else
    exec /usr/sbin/nginx -g 'daemon off;'
fi
SH

RUN chmod +x /etc/service/nginxng/run

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
RUN  chmod +x /etc/my_init.d/05-configure-nginx-port.sh
# Database migration pre-start task
RUN printf '%s\n' '#!/bin/sh' 'echo "Running database migration..." && /opt/venv/bin/python manage.py migrate' > /etc/my_init.d/01-migrate.sh \
    && chmod +x /etc/my_init.d/01-migrate.sh
# Static files pre-start task
RUN printf '%s\n' '#!/bin/sh' 'echo "Running static files collection..." && /opt/venv/bin/python manage.py collectstatic --noinput || true' > /etc/my_init.d/02-collectstatic.sh \
    && chmod +x /etc/my_init.d/02-collectstatic.sh

# Overwrite /etc/my_init.d/10_syslog-ng.init with a permission-tolerant script
RUN cat > /etc/my_init.d/10_syslog-ng.init <<'SH'
#!/bin/bash
set -em

# If /dev/log is either a named pipe or it was placed there accidentally,
# e.g. because of the issue documented at https://github.com/phusion/baseimage-docker/pull/25,
# then we remove it.
if [ ! -S /dev/log ]; then rm -f /dev/log; fi
if [ ! -S /var/lib/syslog-ng/syslog-ng.ctl ]; then rm -f /var/lib/syslog-ng/syslog-ng.ctl; fi

# determine output mode on /dev/stdout because of the issue documented at https://github.com/phusion/baseimage-docker/issues/468
if [ -p /dev/stdout ]; then
    sed -i 's/##SYSLOG_OUTPUT_MODE_DEV_STDOUT##/pipe/' /etc/syslog-ng/syslog-ng.conf
else
    sed -i 's/##SYSLOG_OUTPUT_MODE_DEV_STDOUT##/file/' /etc/syslog-ng/syslog-ng.conf
fi

# If /var/log is writable by another user logrotate will fail
# Only attempt to change ownership if running as root, or if chown is permitted.
if [ "$(id -u)" -eq 0 ]; then
    /bin/chown root:root /var/log
    /bin/chmod 0755 /var/log
else
    if /bin/chown root:root /var/log 2>/dev/null; then
        /bin/chmod 0755 /var/log 2>/dev/null || true
    else
        echo "Skipping chown/chmod on /var/log: insufficient permissions" >&2
    fi
fi

PIDFILE="/var/run/syslog-ng.pid"
SYSLOGNG_OPTS=""

[ -r /etc/default/syslog-ng ] && . /etc/default/syslog-ng

syslogng_wait() {
        if [ "$2" -ne 0 ]; then
                return 1
        fi

        RET=1
        for i in $(seq 1 30); do
                status=0
                syslog-ng-ctl stats >/dev/null 2>&1 || status=$?
                if [ "$status" != "$1" ]; then
                        RET=0
                        break
                fi
                sleep 1s
        done
        return $RET
}

/usr/sbin/syslog-ng --pidfile "$PIDFILE" -F $SYSLOGNG_OPTS &
        # Try to start syslog-ng but do not fail the entire container if it cannot start.
        /usr/sbin/syslog-ng --pidfile "$PIDFILE" -F $SYSLOGNG_OPTS >/dev/null 2>&1 &
        sleep 0.5
        PID=$!
        if ! kill -0 "$PID" 2>/dev/null; then
            echo "syslog-ng failed to start; continuing without syslog-ng" >&2
            exit 0
        fi
        # Optionally wait for proper initialization but ignore failures
        syslogng_wait 1 0 || true
SH
RUN chmod +x /etc/my_init.d/10_syslog-ng.init

# Patch /etc/my_init.d/10_syslog-ng.init to check if user is root, or chown has permissions


EXPOSE 80

# Start container with Phusion's init which will run Nginx + Passenger
CMD ["/sbin/my_init"]

