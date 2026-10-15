"""Settings for local development and secure environment-driven production."""

import os
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


PRODUCTION = env_bool("DJANGO_PRODUCTION", False)
DEBUG = env_bool("DJANGO_DEBUG", not PRODUCTION)

_development_secret = "django-insecure-development-only-change-me-before-deployment"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", _development_secret)
if PRODUCTION and SECRET_KEY == _development_secret:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")
if PRODUCTION and DEBUG:
    raise ImproperlyConfigured("DJANGO_DEBUG must be False in production.")

SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000").rstrip("/")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Vercel supplies the deployment hostname without a scheme. Trust only that exact
# host; custom domains and wildcard preview domains remain explicit configuration.
_vercel_url = os.getenv("VERCEL_URL", "").strip()
if _vercel_url:
    _vercel_host = urlparse(f"//{_vercel_url}").hostname
    if _vercel_host and _vercel_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_vercel_host)
    _vercel_origin = f"https://{_vercel_host}" if _vercel_host else ""
    if _vercel_origin and _vercel_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_vercel_origin)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "accounts",
    "complaints",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "campusfix.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "complaints.context_processors.notification_counts",
            ],
        },
    },
]

WSGI_APPLICATION = "campusfix.wsgi.application"
ASGI_APPLICATION = "campusfix.asgi.application"

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if PRODUCTION and not DATABASE_URL:
    raise ImproperlyConfigured(
        "DATABASE_URL must be set in production; configure the Neon connection string "
        "in Vercel Project Settings."
    )

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=0,
            conn_health_checks=True,
            ssl_require=PRODUCTION,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

USE_S3_MEDIA = env_bool("USE_S3_MEDIA", False)
if USE_S3_MEDIA:
    _required_s3_variables = (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_STORAGE_BUCKET_NAME",
        "AWS_S3_ENDPOINT_URL",
    )
    _missing_s3_variables = [name for name in _required_s3_variables if not os.getenv(name)]
    if _missing_s3_variables:
        raise ImproperlyConfigured(
            "USE_S3_MEDIA requires: " + ", ".join(_missing_s3_variables)
        )

    _s3_options = {
        "access_key": os.environ["AWS_ACCESS_KEY_ID"],
        "secret_key": os.environ["AWS_SECRET_ACCESS_KEY"],
        "bucket_name": os.environ["AWS_STORAGE_BUCKET_NAME"],
        "endpoint_url": os.environ["AWS_S3_ENDPOINT_URL"],
        "region_name": os.getenv("AWS_S3_REGION_NAME") or None,
        "default_acl": None,
        "file_overwrite": False,
        "querystring_auth": env_bool("AWS_QUERYSTRING_AUTH", True),
        "object_parameters": {"CacheControl": "max-age=86400"},
    }
    _custom_domain = os.getenv("AWS_S3_CUSTOM_DOMAIN", "").strip()
    if _custom_domain:
        _s3_options["custom_domain"] = _custom_domain
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": _s3_options,
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"

# Activate transport and cookie protections only in explicit production mode.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = PRODUCTION
SESSION_COOKIE_SECURE = PRODUCTION
CSRF_COOKIE_SECURE = PRODUCTION
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "31536000")) if PRODUCTION else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = PRODUCTION and env_bool(
    "DJANGO_HSTS_INCLUDE_SUBDOMAINS", True
)
SECURE_HSTS_PRELOAD = PRODUCTION and env_bool("DJANGO_HSTS_PRELOAD", True)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
