# python
from pathlib import Path
from datetime import timedelta
from decouple import config

# google
from google.auth import default
from google.cloud.storage import Client

# celery
from celery.schedules import crontab

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

credentials, project_id = default()
storage_client = Client(credentials=credentials)

MEDIA_URL = f'https://storage.googleapis.com/{config('GS_BUCKET_NAME')}/userimages/'
STATIC_URL = f'https://storage.googleapis.com/{config('GS_BUCKET_NAME')}/defaults/'


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
    'activities',
    'assessments',
    'chats',
    'classes',
    'grades',
    'timetables',
    'auth_tokens',
    'uploads',
    
    # third party apps
    'corsheaders', # handle cors 
    'django_redis', # redis caching
    'channels', # django channels 
    'storages', # allows communication with google storage bucket
    'django_celery_beat',
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


# cors config
# origins/domains allowed to communicate with the application in production
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS').split(',')


# allowed methods
CORS_ALLOW_METHODS = config('CORS_ALLOW_METHODS').split(',')


# cors credentials
# allows credentials (cookies, authorization headers, or TLS client certificates) to be sent in cross-origin requests.
CORS_ALLOW_CREDENTIALS = True 
SESSION_COOKIE_DOMAIN = '.seeran-grades.cloud'
CSRF_COOKIE_DOMAIN = '.seeran-grades.cloud'


# applications default user model
# our custom user model 
AUTH_USER_MODEL = 'users.CustomUser'


# user authenticator
# our custom authentication backend
AUTHENTICATION_BACKENDS = [
    'authentication.auth_backends.EmailOrIdNumberModelBackend',
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
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),  # Short-lived access token (adjust as needed)
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=24),    # Longer-lived refresh token (adjust as needed)
    'ROTATE_REFRESH_TOKENS': False,                  # Set to True if you want to rotate refresh tokens
    
    'TOKEN_BLACKLIST_ENABLED': True,
    'TOKEN_BLACKLIST_MODEL': 'rest_framework_simplejwt.token_blacklist.BlacklistedToken',
    # Other settings (e.g., ALGORITHM, SIGNING_KEY, etc.) can be customized as well
}


# celery beat scheduler
CELERY_BEAT_SCHEDULE = {
    'bill_users': {
        'task': 'balances.tasks.bill_users',  # Replace with the actual path to your task
        'schedule': crontab(hour='0,8,16'), # to run task at midnight, 8 AM, and 4 PM
    },
}


"""
    is necessary for Django Channels to know where and how to send/receive messages over the network. 
    It's separate from Django's cache framework, which is why it needs its own configuration
"""
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('CACHE_LOCATION')],
        },
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
        'LOCATION': config('CACHE_LOCATION'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection._HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.connection.BlockingConnectionPool',  # Use BlockingConnectionPool for SSL
            'CONNECTION_POOL_KWARGS': {'ssl_ca_certs': '/home/seeran_grades2/seeran_backend/seeran_backend/server-ca.pem'}, # as done here
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
ASGI_APPLICATION = "seeran_backend.routing.application"


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
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# settings.py


# model id prefixes
# user model : UA
# school model : SA
# activity model : AI
# assessment model : AS
# balance model : BL
# bill model : BI
# bug report model : BR
# chat model : CH
# classroom model : CR
# email ban : EB
# grade model : GR
# schedule model : SC
# teacherschedule : TS
# groudschedule : GS
# Announcement : AN