"""Production settings: fail closed on transport and secret configuration."""

from . import base
from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = base.env_list("DJANGO_ALLOWED_HOSTS")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
