# Copy this file to settings_local.py and fill out appropriately

DEBUG = 
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)
MANAGERS = ADMINS

TIME_ZONE = 'America/New_York'

DB_DEFAULT = {
    'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
    'NAME': '',                      # Or path to database file if using sqlite3.
    'USER': '',                      # Not used with sqlite3.
    'PASSWORD': '',                  # Not used with sqlite3.
    'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
    'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
}

MEDIA_ROOT = ''
STATIC_ROOT = ''

# special settings_local setting that should be set to the abs
# path of the django root directory. many other absolute-path
# settings (e.g. STATICFILES_DIRS, TEMPLATE_DIRS) use this
ROOT_DIR = ''   # DON'T include trailing slash