from .base import *  # noqa: F403,F401


DEBUG = False
DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
ALLOWED_NUM_QUESTIONS = [1, 3, 5, 10]  # noqa: F405
