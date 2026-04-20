"""
Development settings — import everything from production settings,
then override the parts that break local development.

Usage:
    python manage.py runserver --settings=hrms.settings_dev
"""

from .settings import *  # noqa: F401, F403

# ── Core ──────────────────────────────────────────────────────
DEBUG = True
SECRET_KEY = 'dev-only-secret-key-not-for-production'
ALLOWED_HOSTS = ['*']

# ── Kill all HTTPS/SSL enforcement ────────────────────────────
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ── Email — print to console instead of sending ───────────────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'