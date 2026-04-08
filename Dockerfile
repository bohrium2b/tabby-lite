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
# Enable nginx
RUN rm -f /etc/service/nginx/down
EXPOSE 80

# Start container with Phusion's init which will run Nginx + Passenger
CMD ["/sbin/my_init"]

