from pathlib import Path
from datetime import timedelta
from decouple import config


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-1hrd@6u+u$0ouahd*z)v5ra+hu1nn&ljum=oh(r0i3noxbsg7i'

DEBUG = True

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = config('DEBUG', default=False, cast=bool)

if not DEBUG:
    ALLOWED_HOSTS = ["*"]
    
ALLOWED_HOSTS = ["*"]


# Application definition
# installed apps

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # project apps 
    'authentication',
    'schools',
    
    # third party apps
]

# project middleware

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    
    # cors headers middleware
    'corsheaders.middleware.CorsMiddleware',
    
    # projects middleware
    'authentication.middleware.TokenValidationMiddleware',
    
    # django middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# cors config

if not DEBUG:
    CORS_ALLOWED_ORIGINS = [
        'https://www.seeran-grades.com',
        # Add other allowed origins as needed
    ]
    
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'https://www.seeran-grades.com',
    # Add other allowed origins as needed
]

CORS_ALLOW_CREDENTIALS = True

# rest framework config

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

# simplejwt config

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),  # Short-lived access token (adjust as needed)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),    # Longer-lived refresh token (adjust as needed)
    'ROTATE_REFRESH_TOKENS': False,                  # Set to True if you want to rotate refresh tokens
    
    'TOKEN_BLACKLIST_ENABLED': True,
    'TOKEN_BLACKLIST_MODEL': 'rest_framework_simplejwt.token_blacklist.BlacklistedToken',
    # Other settings (e.g., ALGORITHM, SIGNING_KEY, etc.) can be customized as well
}

# Caching config

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Email sending config


# default settings 

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
WSGI_APPLICATION = 'seeran_backend.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'seeran_database',
        'USER': 'tsholo',
        'PASSWORD': 'N4Hoj5Mjrw4BEGvfWZAB',
        'HOST': 'seeran-database.cz4cqeskmn2k.af-south-1.rds.amazonaws.com',
        'PORT': '5432',
    }
}

# SSH

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True



# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# user authenticator

AUTHENTICATION_BACKENDS = [
    'authentication.auth_backends.EmailOrIdNumberModelBackend',
    'django.contrib.auth.backends.ModelBackend',
    # Add other authentication backends if needed
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# default user model
AUTH_USER_MODEL = 'authentication.CustomUser'
