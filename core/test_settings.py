"""Isolation tests for local and production settings modes."""

import json
import os
import subprocess
import sys

from django.test import SimpleTestCase


SETTINGS_ENVIRONMENT_NAMES = {
    "DATABASE_URL", "DJANGO_ALLOWED_HOSTS", "DJANGO_CSRF_TRUSTED_ORIGINS",
    "DJANGO_DEBUG", "DJANGO_HSTS_INCLUDE_SUBDOMAINS", "DJANGO_HSTS_PRELOAD",
    "DJANGO_HSTS_SECONDS", "DJANGO_PRODUCTION", "DJANGO_SECRET_KEY", "SITE_URL",
    "USE_S3_MEDIA", "VERCEL_URL", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
    "AWS_STORAGE_BUCKET_NAME", "AWS_S3_ENDPOINT_URL", "AWS_S3_REGION_NAME",
    "AWS_S3_CUSTOM_DOMAIN", "AWS_QUERYSTRING_AUTH",
}


class EnvironmentSettingsTests(SimpleTestCase):
    def run_settings_probe(self, extra_environment=None):
        environment = {
            key: value for key, value in os.environ.items()
            if key not in SETTINGS_ENVIRONMENT_NAMES
        }
        environment.update(extra_environment or {})
        code = """
import json
from campusfix import settings
print(json.dumps({
    'database_engine': settings.DATABASES['default']['ENGINE'],
    'database_name': str(settings.DATABASES['default']['NAME']),
    'debug': settings.DEBUG,
    'production': settings.PRODUCTION,
    'allowed_hosts': settings.ALLOWED_HOSTS,
    'csrf_origins': settings.CSRF_TRUSTED_ORIGINS,
    'site_url': settings.SITE_URL,
    'default_storage': settings.STORAGES['default']['BACKEND'],
    'static_storage': settings.STORAGES['staticfiles']['BACKEND'],
    'ssl_redirect': settings.SECURE_SSL_REDIRECT,
    'secure_session': settings.SESSION_COOKIE_SECURE,
    'secure_csrf': settings.CSRF_COOKIE_SECURE,
    'hsts_seconds': settings.SECURE_HSTS_SECONDS,
    'secret_was_supplied': settings.SECRET_KEY == 'test-only-production-secret-not-output',
}))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=os.fspath(os.path.dirname(os.path.dirname(__file__))),
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertNotIn("test-only-production-secret-not-output", result.stdout)
        return json.loads(result.stdout)

    def test_local_defaults_keep_sqlite_and_filesystem_media(self):
        settings = self.run_settings_probe()

        self.assertEqual(settings["database_engine"], "django.db.backends.sqlite3")
        self.assertTrue(settings["database_name"].endswith("db.sqlite3"))
        self.assertTrue(settings["debug"])
        self.assertFalse(settings["production"])
        self.assertEqual(
            settings["default_storage"], "django.core.files.storage.FileSystemStorage"
        )
        self.assertFalse(settings["ssl_redirect"])
        self.assertEqual(settings["hsts_seconds"], 0)

    def test_production_accepts_environment_settings_without_printing_secrets(self):
        settings = self.run_settings_probe({
            "DJANGO_PRODUCTION": "True",
            "DJANGO_DEBUG": "False",
            "DJANGO_SECRET_KEY": "test-only-production-secret-not-output",
            "DJANGO_ALLOWED_HOSTS": "campusfix.example",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://campusfix.example",
            "SITE_URL": "https://campusfix.example",
            "DATABASE_URL": "postgresql://test_user:test_password@db.example/test_db",
            "USE_S3_MEDIA": "True",
            "AWS_ACCESS_KEY_ID": "test-access-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret-key",
            "AWS_STORAGE_BUCKET_NAME": "test-bucket",
            "AWS_S3_ENDPOINT_URL": "https://objects.example",
        })

        self.assertEqual(settings["database_engine"], "django.db.backends.postgresql")
        self.assertEqual(settings["database_name"], "test_db")
        self.assertFalse(settings["debug"])
        self.assertTrue(settings["production"])
        self.assertTrue(settings["secret_was_supplied"])
        self.assertEqual(settings["allowed_hosts"], ["campusfix.example"])
        self.assertEqual(settings["csrf_origins"], ["https://campusfix.example"])
        self.assertEqual(settings["site_url"], "https://campusfix.example")
        self.assertEqual(settings["default_storage"], "storages.backends.s3.S3Storage")
        self.assertTrue(settings["ssl_redirect"])
        self.assertTrue(settings["secure_session"])
        self.assertTrue(settings["secure_csrf"])
        self.assertEqual(settings["hsts_seconds"], 31536000)
