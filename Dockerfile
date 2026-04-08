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

# Use PIP to install from pyproject.toml
RUN pip install --upgrade pip setuptools wheel && pip install -e .


# Collect static files using the venv python (explicit path avoids wrong python)
RUN python manage.py collectstatic --noinput || true

# Ensure Nginx sites-enabled and copy our sample Passenger config
RUN mkdir -p /etc/nginx/sites-enabled
COPY deploy/nginx.passenger.conf /etc/nginx/sites-enabled/app.conf

EXPOSE 80

# Start container with Phusion's init which will run Nginx + Passenger
CMD ["/sbin/my_init"]

