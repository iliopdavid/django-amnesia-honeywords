import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from django_honeywords.models import AmnesiaSet


@pytest.mark.django_db
def test_amnesia_init_user_command(settings):
    settings.HONEYWORDS = {"AMNESIA_K": 5, "AMNESIA_P_MARK": 0.0, "AMNESIA_P_REMARK": 0.0}

    User = get_user_model()
    User.objects.create_user(username="bob")

    call_command("amnesia_init_user", "bob", "--password", "Secret123")

    aset = AmnesiaSet.objects.get(user__username="bob")
    assert aset.k == 5
    assert aset.credentials.count() == 5
