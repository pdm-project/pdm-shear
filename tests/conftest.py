import pytest


@pytest.fixture
def mock_data(monkeypatch):
    data = {
        "requests": ["requests"],
        "flask": ["flask"],
        "python-multipart": ["python_multipart", "multipart"],
        "django": ["django"],
        "rich": ["rich"],
    }
    monkeypatch.setattr("pdm_shear.main._local_cache", data)
