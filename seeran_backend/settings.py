# python
import os
import ssl
from pathlib import Path
from datetime import timedelta
from decouple import config


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')


# uplaod image max-size 
DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400  # 25 MB


# SECURITY WARNING: don't run with debug turned on in production!
# activates debug mode for the application
DEBUG = config('DEBUG')

# Application definition
# a list of all installed apps
INSTALLED_APPS = [

    "daphne",
    
    # django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    # 'django.contrib.staticfiles',  Can be removed if not using static files

    # project apps
    'authentication',

    'accounts',
    'account_access_tokens',
    'email_address_bans',
    'account_permissions',
    'permission_groups',

    'audit_logs',

    'schools',
    'school_announcements',

    'grades',

    'subjects',
    'topics',
    'student_subject_performances',

    'terms',
    'term_subject_performances',

    'classrooms',
    'classroom_performances',
    'assessments',
    'assessment_submissions',
    'assessment_transcripts',

    'school_attendances',
    'student_activities',
    'student_progress_reports',
    'student_group_timetables',

    'teacher_timetables',

    'timetables',
    'timetable_sessions',

    'balances',
    'invoices',

    'chat_rooms',
    'chat_room_messages',

    'bug_reports',

    'emergencies',

    'uploads',
    
    # third party apps
    'corsheaders', # handle cors 
    'django_redis', # redis caching
    'django_celery_results', # celery db communication
    # 'django_celery_beat',
    'channels', # django channels 
    # 'storages', # allows communication with google storage bucket
]


# project middleware
# all project middleware
MIDDLEWARE = [
    
    # cors headers middleware
    'corsheaders.middleware.CorsMiddleware',

    # django middleware
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    # project middleware
    # none
    
    # django middleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# These headers are important because they:
# Prevent attacks: Help mitigate common vulnerabilities like XSS, clickjacking, and data injection.
# Enforce security policies: Ensure that your application is accessed in a secure manner.
# Enhance trust: Signal to users and browsers that your site is committed to security best practices.
MIDDLEWARE += [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]



# Purpose: This setting is used to specify which domains are allowed to make cross-origin requests to your Django application.
# Usage: It's part of the CORS (Cross-Origin Resource Sharing) configuration, 
# which controls how resources on your server can be accessed by web pages from other domains.
# Format: The CORS_ALLOWED_ORIGINS setting is a list of URLs that represent the allowed origins.
# For example, https://www.example.cloud and https://example:3000 are allowed to interact with your API.
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS').split(',')


# Purpose: This setting specifies a list of host/domain names that your Django application can serve.
# It’s used to prevent HTTP Host header attacks.
# Usage: Django uses this setting to validate the Host header in incoming HTTP requests.
# Requests with a Host header not listed in ALLOWED_HOSTS will be denied.
# Format: It’s usually a list of strings. In your example, 'proxy.seeran-grades.cloud' is the only allowed host.
ALLOWED_HOSTS = config('ALLOWED_HOSTS').split(',')


# allowed methods
CORS_ALLOW_METHODS = config('CORS_ALLOW_METHODS').split(',')


# cors credentials
# allows credentials (cookies, authorization headers, or TLS client certificates) to be sent in cross-origin requests.
CORS_ALLOW_CREDENTIALS = True 
SESSION_COOKIE_DOMAIN = '.seeran-grades.cloud'
CSRF_COOKIE_DOMAIN = '.seeran-grades.cloud'


# applications default user model
# our custom user model 
AUTH_USER_MODEL = 'accounts.BaseAccount'


# user authenticator
# our custom authentication backend
AUTHENTICATION_BACKENDS = [
    # 'authentication.auth_backends.EmailOrIdNumberModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]


# rest framework config
# default authentication method
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ]
}


# simplejwt config
# Define JWT_AUTH_COOKIE setting
JWT_AUTH_COOKIE = 'access_token'

# simplejwt token settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),  # long-lived access token
    'REFRESH_TOKEN_LIFETIME': timedelta(seconds=0),    # Longer-lived refresh token (adjust as needed)
    'ROTATE_REFRESH_TOKENS': False,                  # Set to True if you want to rotate refresh tokens
    
    'TOKEN_BLACKLIST_ENABLED': False,
    'TOKEN_BLACKLIST_MODEL': 'rest_framework_simplejwt.token_blacklist.BlacklistedToken',
    # Other settings (e.g., ALGORITHM, SIGNING_KEY, etc.) can be customized as well
}




"""
    is necessary for Django Channels to know where and how to send/receive messages over the network. 
    It's separate from Django's cache framework, which is why it needs its own configuration
"""
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts":[{
                "address": 'rediss://' + config('CACHE_LOCATION') + ':6378',
                "ssl_cert_reqs": None,
            }]
        },
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection._HiredisParser',
        }
    },
}



"""
    If your Redis server is using a self-signed certificate or a certificate from an internal CA, 
    ensure that the CA certificate chain is correctly configured on the Django application server. 
    You may need to specify the path to the CA certificate or the entire certificate chain in your Django settings.
"""
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'rediss://' + config('CACHE_LOCATION') + ':6378',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection._HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.connection.BlockingConnectionPool',  # Use BlockingConnectionPool for SSL
            'CONNECTION_POOL_KWARGS': {'ssl_ca_certs': config('SERVER_CA_CERT')}, # as done here
        }
    }
}


# postfres database
# application database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_ENDPOINT'),
        'PORT': '5432',
    }
}
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#     }
# }


CELERY_IMPORTS = (
    'term_subject_performances.tasks',
    'student_subject_performances.tasks',
    'classrooms.tasks',
    'assessments.tasks',
    # Add other app tasks here
)

# Celery settings
CELERY_BROKER_URL = 'rediss://' + config('CACHE_LOCATION') + ':6378'
CELERY_RESULT_BACKEND = 'django-db'  # Store task results in Django's database
CELERY_TASK_RESULT_EXPIRES = 3600  # Time in seconds after which task results will expire

CELERY_BROKER_TRANSPORT_OPTIONS = {
    'ssl': {
        'ssl_cert_reqs': ssl.CERT_REQUIRED,  # Ensure SSL certificate verification is required
        'ssl_ca_certs': config('SERVER_CA_CERT'),  # Path to your CA certificate
    }
}

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# With this configuration, tasks will run in the Django process, allowing you to use regular Django debugging techniques like breakpoints and error handling.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True  # Propagate exceptions

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'celery': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}


# ssl config
# configures the application to commmunicate in https
if not DEBUG:
    # What it does: Tells Django that the request was originally made via HTTPS, even if your proxy (e.g., Nginx) forwards it as HTTP.
    # Why it's important: Ensures secure communication from clients to your application, especially when behind a proxy.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # What it does: Redirects all HTTP requests to HTTPS.
    # Why it's important: Ensures all communication is encrypted.
    SECURE_SSL_REDIRECT = True

    # What it does: Ensures that cookies with the session data are only sent over HTTPS.
    # Why it's important: Protects session data from being intercepted.
    SESSION_COOKIE_SECURE = True

    # What it does: Ensures that cookies with the CSRF token are only sent over HTTPS.
    # Why it's important: Protects against Cross-Site Request Forgery attacks by ensuring tokens are only sent over secure connections.
    CSRF_COOKIE_SECURE = True

    # What it does: Prevents your site from being displayed in a frame (e.g., iframe).
    # Why it's important: Protects against clickjacking attacks.
    X_FRAME_OPTIONS = 'DENY'

    # What it does: Enables the browser’s XSS protection.
    # Why it's important: Adds an extra layer of protection against cross-site scripting (XSS) attacks.
    SECURE_BROWSER_XSS_FILTER = True

    # What it does: Prevents browsers from interpreting files as a different MIME type than what is specified.
    # Why it's important: Protects against attacks based on MIME-type confusion.
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # What it does: Enforces the use of HTTPS by telling browsers to only connect to your site over HTTPS for the next year.
    # Why it's important: Ensures that future connections to your site are secure.
    SECURE_HSTS_SECONDS = 31536000  # 1 year

    # What it does: Applies HSTS (HTTP Strict Transport Security) to all subdomains.
    # Why it's important: Ensures that all subdomains are also accessed securely.
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    # What it does: Indicates to browsers that your site is eligible for inclusion in the HSTS preload list.
    # Why it's important: Ensures that your site and all its subdomains are accessed securely from the first connection.
    SECURE_HSTS_PRELOAD = True


# default settings 
# the rest are default django settigns
ROOT_URLCONF = 'seeran_backend.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# seeran_backend/settings.py
# WSGI_APPLICATION = 'seeran_backend.wsgi.application'
ASGI_APPLICATION = "seeran_backend.asgi.application"


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'authentication.validators.PasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
