"""ASGI entry point. There is intentionally no WSGI entry point in this service."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

from django.core.asgi import get_asgi_application  # noqa: E402

application = get_asgi_application()
