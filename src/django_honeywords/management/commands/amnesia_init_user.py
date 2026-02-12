from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from django_honeywords.amnesia_service import amnesia_initialize
from django_honeywords.conf import get_setting


class Command(BaseCommand):
    help = "Initialize Amnesia credentials for a user."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--password", required=True)
        parser.add_argument("--k", type=int, default=None)
        parser.add_argument("--p-mark", type=float, default=None)
        parser.add_argument("--p-remark", type=float, default=None)

    def handle(self, *args, **opts):
        username = opts["username"]
        password = opts["password"]

        k = opts["k"]
        p_mark = opts["p_mark"]
        p_remark = opts["p_remark"]

        if k is None:
            k = int(get_setting("AMNESIA_K"))
        if p_mark is None:
            p_mark = float(get_setting("AMNESIA_P_MARK"))
        if p_remark is None:
            p_remark = float(get_setting("AMNESIA_P_REMARK"))

        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User not found: {username}")

        amnesia_initialize(user, password, k=k, p_mark=p_mark, p_remark=p_remark)
        self.stdout.write(self.style.SUCCESS(f"Initialized Amnesia for {username} (k={k}, p_mark={p_mark}, p_remark={p_remark})"))
