"""
Django settings for project.

Generated by 'django-admin startproject' using Django 3.0.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
import sys

import dj_database_url  # needed for DigitalOcean database connection

from simmate import website  # needed to specify location of apps
from simmate import database  # needed to specify location of database

# from simmate.configuration.django import settings_user  # to allow extra apps supplied by user

# The base directory is where simmate.website is located. Note this is Django's
# base directory, NOT simmates
BASE_DIR = os.path.dirname(os.path.abspath(website.__file__))

# The database directory is where simmate.database is located. I move the
# default database file into the simmate.database module.
# TODO: consider placing the database in the user's .simmate/ configuration
# directory so they can easily share/delete it.
DATABASE_DIR = os.path.dirname(os.path.abspath(database.__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# For DigitalOcean, we grab this secret key from an enviornment variable.
# If this variable isn't set, then we instead generate a random one.
from django.core.management.utils import get_random_secret_key

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", get_random_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
# For DigitalOcean, we try grabbing this from an enviornment variable. If that
# variable isn't set, then we assume we are debugging. The == at the end converts
# the string to a boolean for us.
DEBUG = os.getenv("DEBUG", "True") == "True"

# To make this compatible with DigitalOcean, we try to grab the allowed hosts
# from an enviornment variable, which we then split into a list. If this
# enviornment variable isn't set yet, then we just defaul to the localhost.
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# List all applications that Django will initialize with. Write the full python
# path to the app or it's config file. Note that relative python paths work too
# if you are developing a new app. Advanced users can remove unnecessary apps
# if you'd like to speed up django's start-up time.
INSTALLED_APPS = [
    #
    # These are all apps that are built by Simmate
    "simmate.website.accounts.apps.AccountsConfig",
    "simmate.website.third_parties.apps.ThirdPartyConfig",
    # "simmate.website.execution.apps.ExecutionConfig",  # using Prefect instead
    #
    # These are built-in django apps that we use for extra features
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Other apps installed with Django to consider
    #   "django.contrib.humanize",
    #   "django.contrib.postgres",
    #   "django.contrib.redirects",
    #   "django.contrib.sitemaps",
    #
    # These are apps created by third-parties that give us extra features
    "crispy_forms",  # django-crispy-forms
    "rest_framework",  # djangorestframework
    "django_filters",  # django-filter
    'django_extensions',  # for development tools
    # Other third-party apps/tools to consider. Note that some of these don't
    # need to be installed apps while some also request different setups.
    #   django-extensions
    #   django-ratelimit
    #   dj-stripe
    #   django-allauth
    #   django-debug-toolbar
    #   django-channels (+ React.js)
    #   django-REST-framework
    #   django-graphene (+ GraphQL)
    #   django-redis
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# "core" here is based on the name of my main django folder
ROOT_URLCONF = "simmate.website.core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # I set DIRS below so I can have a single templates folder
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# "core" here is based on the name of my main django folder
WSGI_APPLICATION = "simmate.website.core.wsgi.application"

# -----------------------
# Database Connection
# Note that the database we connect to depends on whether we are testing things
# locally or running things in production! So we use DEVELOPMENT_MODE setting
# to decide how to connect.
#
# This is a DigitalOcean keyword that we use to help with alternative configurations.
# For example, we could use this to decide which database to connect to below. It
# defaults to True unless it's set otherwise in the enviornment.
# The == "True" at the end converts this to a boolean for us.
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "True") == "True"
#
# If we are in development mode, then we only connect to our local SQLite database.
# Alternatively, we would connect to a personal PostgreSQL database -- which I have
# an example of this commented out below.
if DEVELOPMENT_MODE is True:
    DATABASES = {
        # "default": {
        #     "ENGINE": "django.db.backends.sqlite3",
        #     "NAME": os.path.join(DATABASE_DIR, "db.sqlite3"),
        # }
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": "simmate-database",  # default on DigitalOcean is defaultdb
            "USER": "doadmin",
            "PASSWORD": "dibi5n3varep5ad8",
            "HOST": "db-postgresql-nyc3-09114-do-user-8843535-0.b.db.ondigitalocean.com",
            "PORT": "25060",
            "OPTIONS": {"sslmode": "require"},  # !!! is this needed?
            # "CONN_MAX_AGE": 0,  # set this to higher value for production website server
        }
    }
# When DigitalOcean runs the "collectstatic" command, we don't want to connect
# any database. So we use the "sys" library to look at the command and ensure
# it doesn't involve "collectstatic". Otherwise we use the URL that is set with
# our enviornment variable.
elif len(sys.argv) > 0 and sys.argv[1] != "collectstatic":
    # ensure that we have the database URL properly configured in DigitalOcean
    if os.getenv("DATABASE_URL", None) is None:
        raise Exception("DATABASE_URL environment variable not defined")
    # Now connect our DigitalOcean to this database!
    DATABASES = {
        "default": dj_database_url.parse(os.environ.get("DATABASE_URL")),
    }
    # NOTE: this line above is the same as doing...
    # DATABASES = {
    #     "default": {
    #         "ENGINE": "django.db.backends.postgresql_psycopg2",
    #         "NAME": "simmate-database-pool",  # default on DigitalOcean is defaultdb
    #         "USER": "doadmin",
    #         "PASSWORD": "dibi5n3varep5ad8",
    #         "HOST": "db-postgresql-nyc3-09114-do-user-8843535-0.b.db.ondigitalocean.com",
    #         "PORT": "25061",
    #         "OPTIONS": {"sslmode": "require"},  # !!! is this needed?
    #         # "CONN_MAX_AGE": 0,  # set this to higher value for production website server
    #     }
    # }

# -----------------------

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth."
            "password_validation.UserAttributeSimilarityValidator"
        ),  # formatted in this odd way because of line length limit for Black
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

DATETIME_INPUT_FORMATS = [
    "%Y-%m-%dT%H:%M",  # this is a custom format I added to get my form widgets working.
    "%Y-%m-%d %H:%M:%S",  # '2006-10-25 14:30:59'
    "%Y-%m-%d %H:%M:%S.%f",  # '2006-10-25 14:30:59.000200'
    "%Y-%m-%d %H:%M",  # '2006-10-25 14:30'
    "%Y-%m-%d",  # '2006-10-25'
    "%m/%d/%Y %H:%M:%S",  # '10/25/2006 14:30:59'
    "%m/%d/%Y %H:%M:%S.%f",  # '10/25/2006 14:30:59.000200'
    "%m/%d/%Y %H:%M",  # '10/25/2006 14:30'
    "%m/%d/%Y",  # '10/25/2006'
    "%m/%d/%y %H:%M:%S",  # '10/25/06 14:30:59'
    "%m/%d/%y %H:%M:%S.%f",  # '10/25/06 14:30:59.000200'
    "%m/%d/%y %H:%M",  # '10/25/06 14:30'
    "%m/%d/%y",  # '10/25/06'
]

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
# !!! Consider removing in the future.
USE_I18N = True

# !!! I changed this setting to get my datetime-local widgets working, but I don't
# !!! understand active locals -- I need to read more
# !!! https://docs.djangoproject.com/en/3.0/ref/forms/fields/#datetimefield
USE_L10N = False

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
# collect by running 'python manage.py collectstatic'
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

# This sets the django-crispy formating style
CRISPY_TEMPLATE_PACK = "bootstrap4"

# options for login/logoff
# LOGIN_REDIRECT_URL = "/accounts/profile/"  # this is the default
LOGOUT_REDIRECT_URL = "/accounts/loginstatus/"

# Settings for sending emails with my gmail account
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"  # this is the default
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "jacksundberg123@gmail.com"  # os.environ.get('EMAIL_USER')
# !!! REMOVE IN PRODUCTION. Use this instead: os.environ.get('EMAIL_PASSWORD')
EMAIL_HOST_PASSWORD = "lqurjxyttrjrlgcr"

# These settings help configure djangorestframework and our REST API
REST_FRAMEWORK = {
    # The default permission needed to access data is simply that the individual
    # in signed into an account. In the future, consider using
    # DjangoModelPermissionsOrAnonReadOnly as default because this will inherit
    # user permissions we assign at the model level in django.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # Because we have a massive number of results for different endpoints,
    # we want to set results to be paginated by 25 results per page. This
    # way we don't have to set a page limit for every individual endpoint
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    # We use django-filter to automatically handle filtering from a REST url
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    # To prevent users from querying too much and bringing down our servers,
    # we set a throttle rate on each user. Here, "anon" represents an anonymous
    # user (not signed-in) while signed-in users have access to higher download
    # rates. Note these are very restrictive because we prefer users to download
    # full databases and use Simmate locally instead.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "100/day", "user": "1000/day"},
}
