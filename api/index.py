"""Expose CampusFix's WSGI application to the Vercel Python runtime."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campusfix.settings")

from campusfix.wsgi import application  # noqa: E402


def app(environ, start_response):
    """Remove Vercel's internal function prefix before Django resolves URLs."""
    path_info = environ.get("PATH_INFO", "")
    for prefix in ("/api/index.py", "/api/index", "/api"):
        if path_info == prefix or path_info.startswith(f"{prefix}/"):
            path_info = path_info[len(prefix):] or "/"
            break
    if path_info in {"/index", "/index.py"}:
        path_info = "/"
    environ["PATH_INFO"] = path_info
    return application(environ, start_response)
