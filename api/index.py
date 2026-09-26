"""Expose CampusFix's WSGI application to the Vercel Python runtime."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campusfix.settings")

from campusfix.wsgi import application  # noqa: E402

app = application
