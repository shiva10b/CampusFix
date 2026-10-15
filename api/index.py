"""Expose CampusFix's WSGI application to the Vercel Python runtime."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campusfix.settings")

from campusfix.wsgi import application  # noqa: E402


def app(environ, start_response):
    """Remove Vercel's internal function prefix before Django resolves URLs."""
    path_info = environ.get("PATH_INFO", "")
    if path_info == "/api" or path_info.startswith("/api/"):
        environ["PATH_INFO"] = path_info[4:] or "/"
    return application(environ, start_response)
