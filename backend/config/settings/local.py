"""Local development settings; production must provide an explicit environment."""

import os

from . import base
from .base import *  # noqa: F401,F403

DEBUG = base.env_bool("DJANGO_DEBUG", "1")
ALLOWED_HOSTS = base.env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
DATABASES = {**base.DATABASES, "default": {**base.DATABASES["default"]}}
DATABASES["default"]["OPTIONS"] = {**base.DATABASES["default"]["OPTIONS"]}
DATABASES["default"]["OPTIONS"]["sslmode"] = os.getenv("POSTGRES_SSLMODE", "prefer")
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
