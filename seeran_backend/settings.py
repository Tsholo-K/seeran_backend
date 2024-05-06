import os

from pathlib import Path
from datetime import timedelta
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')


# uplaod image max-size 
DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400  # 25 MB


# activates debug mode for the application
DEBUG = config('DEBUG')


# SECURITY WARNING: don't run with debug turned on in production!
# sets the ip addresses the application can be hosted from
ALLOWED_HOSTS = ["*"] 


# Application definition
# a list of all installed apps
INSTALLED_APPS = [
    
    # django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # project apps 
    'authentication',
    'schools',
    'users',
    'balances',
    'bug_reports',
    'email_bans',
    
    # third party apps
    'corsheaders', # handle cors 
    'django_redis', # redis caching
    'storages', # allows for the application to read/write to s3 bucket
    'channels', # websockets
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
    
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# cors config
# origins/domains allowed to communicate with the application in production
CORS_ALLOWED_ORIGINS = [
    'https://www.seeran-grades.com',
    'https://server.seeran-grades.com',
    'https://localhost:3000'
    # Add other allowed origins as needed
]


# allowed methods
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]


# cors credentials
# allows credentials (cookies, authorization headers, or TLS client certificates) to be sent in cross-origin requests.
CORS_ALLOW_CREDENTIALS = True 
SESSION_COOKIE_DOMAIN = '.seeran-grades.com'
CSRF_COOKIE_DOMAIN = '.seeran-grades.com'


# applications default user model
# our custom user model 
AUTH_USER_MODEL = 'users.CustomUser'


# user authenticator
# our custom authentication backend
AUTHENTICATION_BACKENDS = [
    'authentication.auth_backends.EmailOrIdNumberModelBackend',
    'django.contrib.auth.backends.ModelBackend',
    # Add other authentication backends if needed
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
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),  # Short-lived access token (adjust as needed)
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=24),    # Longer-lived refresh token (adjust as needed)
    'ROTATE_REFRESH_TOKENS': False,                  # Set to True if you want to rotate refresh tokens
    
    'TOKEN_BLACKLIST_ENABLED': True,
    'TOKEN_BLACKLIST_MODEL': 'rest_framework_simplejwt.token_blacklist.BlacklistedToken',
    # Other settings (e.g., ALGORITHM, SIGNING_KEY, etc.) can be customized as well
}


# redis caching config
# applications caching configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://seeran-redis-database.qqnsrs.clustercfg.afs1.cache.amazonaws.com:6379/',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# redis channel layer
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('redis://seeran-redis-database.qqnsrs.clustercfg.afs1.cache.amazonaws.com:6379/',)],
        },
    },
}


# postfres database
# application database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'seeran_database',
        'USER': 'tsholo',
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': '5432',
    }
}
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#     }
# }


AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
STATIC_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/project_static_files/'

# s3 bucket
# s3 bucket configuration
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "object_parameters": {
                'CacheControl': 'max-age=86400',
            },
            'file_overwrite': False
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "object_parameters": {
                'CacheControl': 'max-age=86400',
            },
            'file_overwrite': False,
            'location': 'project_static_files/',
        },
    },
}



# Email sending config
EMAIL_BACKEND = 'django_ses.SESBackend'


# ssl config
# configures the application to commmunicate in https
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True


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
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
