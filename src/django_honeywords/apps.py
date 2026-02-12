from django.apps import AppConfig


class DjangoHoneywordsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_honeywords"

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.models.signals import pre_save
        from .signals import _on_user_password_change

        User = get_user_model()
        pre_save.connect(_on_user_password_change, sender=User)
