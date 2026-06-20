import pytest

from apps.users.models import User

pytestmark = pytest.mark.django_db


def test_create_user_with_email():
    user = User.objects.create_user(email="a@example.com", password="testpass123")
    assert user.email == "a@example.com"
    assert user.check_password("testpass123")
    assert not user.is_staff


def test_create_superuser():
    admin = User.objects.create_superuser(email="admin@example.com", password="testpass123")
    assert admin.is_staff
    assert admin.is_superuser
