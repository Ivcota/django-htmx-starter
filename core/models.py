from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model. Add fields here as your project grows.

    This exists so you can extend the user model later without the pain
    of migrating away from Django's default auth.User after data exists.
    See: https://docs.djangoproject.com/en/5.2/topics/auth/customizing/
    """

    pass
