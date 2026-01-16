from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from django_honeywords.service import initialize_user_honeywords

class Command(BaseCommand):
    help = "Initialize honeywords for a user (MVP local honeychecker)."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--password", required=True)
        parser.add_argument("--k", type=int, default=20)

    def handle(self, *args, **opts):
        username = opts["username"]
        password = opts["password"]
        k = opts["k"]

        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User not found: {username}")

        initialize_user_honeywords(user, password, k=k)
        self.stdout.write(self.style.SUCCESS(f"Initialized honeywords for {username} (k={k})"))