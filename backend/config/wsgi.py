import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

try:
    from django.core.management import call_command
    print("=== Auto-running Django migrations ===")
    call_command("migrate", interactive=False)
    print("=== Auto-running portal extension schema ===")
    call_command("apply_portal_schema")
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.exception("Failed to auto-run migrations at startup")

