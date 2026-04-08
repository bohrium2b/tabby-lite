import os
import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH (assumes this file sits at repo root)
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Point to the Django settings module used by this project
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tabby_lite.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
