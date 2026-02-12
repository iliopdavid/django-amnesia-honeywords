import pytest
from django.contrib.auth import get_user_model
from django_honeywords.models import AmnesiaSet, AmnesiaCredential

@pytest.mark.django_db
def test_amnesia_models_create():
    User = get_user_model()
    u = User.objects.create_user(username="amnesia_user")

    aset = AmnesiaSet.objects.create(user=u, k=5, p_mark=0.5, p_remark=0.0)
    AmnesiaCredential.objects.create(aset=aset, index=0, password_hash="hash0", marked=True)
    AmnesiaCredential.objects.create(aset=aset, index=1, password_hash="hash1", marked=False)

    assert aset.user_id == u.id
    assert aset.credentials.count() == 2
    assert aset.credentials.get(index=0).marked is True
