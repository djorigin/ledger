import pytest


@pytest.fixture(autouse=True)
def _isolate_media_root(settings, tmp_path):
    """Inventory photo uploads in tests must not land in the real dev
    media/ directory -- every test gets its own throwaway MEDIA_ROOT."""
    settings.MEDIA_ROOT = tmp_path
