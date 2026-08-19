"""Vercel serverless entrypoint: exposes the Django app as WSGI `app`.

Vercel's @vercel/python builder detects the `app` callable and routes
/api/* requests to it (see vercel.json).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_DEBUG", "false")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
