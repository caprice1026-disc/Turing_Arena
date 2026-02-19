from pathlib import Path

import environ


BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "django-insecure-change-me"),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
    USE_MYSQL=(bool, False),
    MYSQL_NAME=(str, "turing_arena"),
    MYSQL_USER=(str, "root"),
    MYSQL_PASSWORD=(str, ""),
    MYSQL_HOST=(str, "127.0.0.1"),
    MYSQL_PORT=(int, 3306),
    OPENROUTER_API_KEY=(str, ""),
    OPENROUTER_BASE_URL=(str, "https://openrouter.ai/api/v1"),
    OPENROUTER_TIMEOUT_SECONDS=(int, 30),
    OPENROUTER_MAX_RETRIES=(int, 3),
    ALLOWED_NUM_QUESTIONS=(str, "1,3,5,10"),
    RESERVE_TTL_HOURS=(int, 24),
    RANKING_MIN_PHASE1=(int, 10),
    RANKING_MIN_PHASE2=(int, 5),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

ALLOWED_NUM_QUESTIONS = [
    int(value.strip())
    for value in env("ALLOWED_NUM_QUESTIONS").split(",")
    if value.strip()
]
RESERVE_TTL_HOURS = env("RESERVE_TTL_HOURS")
RANKING_MIN_PHASE1 = env("RANKING_MIN_PHASE1")
RANKING_MIN_PHASE2 = env("RANKING_MIN_PHASE2")

OPENROUTER_API_KEY = env("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = env("OPENROUTER_BASE_URL")
OPENROUTER_TIMEOUT_SECONDS = env("OPENROUTER_TIMEOUT_SECONDS")
OPENROUTER_MAX_RETRIES = env("OPENROUTER_MAX_RETRIES")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.content",
    "apps.quiz",
    "apps.admin_portal",
    "apps.ranking",
    "apps.pages",
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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if env("USE_MYSQL"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("MYSQL_NAME"),
            "USER": env("MYSQL_USER"),
            "PASSWORD": env("MYSQL_PASSWORD"),
            "HOST": env("MYSQL_HOST"),
            "PORT": env("MYSQL_PORT"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
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

LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.auth_backends.LoginIdOrEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]
