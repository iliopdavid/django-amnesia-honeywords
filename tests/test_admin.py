"""
Verify all models are registered in the Django admin.
"""
import pytest
from django.contrib import admin


@pytest.mark.django_db
def test_admin_registrations():
    from django_honeywords.models import (
        AmnesiaSet,
        HoneywordEvent,
        HoneywordUserState,
    )

    assert admin.site.is_registered(AmnesiaSet)
    assert admin.site.is_registered(HoneywordEvent)
    assert admin.site.is_registered(HoneywordUserState)


@pytest.mark.django_db
def test_event_admin_is_readonly():
    from django_honeywords.admin import HoneywordEventAdmin
    from django_honeywords.models import HoneywordEvent

    model_admin = HoneywordEventAdmin(model=HoneywordEvent, admin_site=admin.site)
    assert model_admin.has_add_permission(request=None) is False
    assert model_admin.has_change_permission(request=None) is False


@pytest.mark.django_db
def test_amnesia_set_admin_no_add():
    from django_honeywords.admin import AmnesiaSetAdmin
    from django_honeywords.models import AmnesiaSet

    model_admin = AmnesiaSetAdmin(model=AmnesiaSet, admin_site=admin.site)
    assert model_admin.has_add_permission(request=None) is False
