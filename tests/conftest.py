import tempfile
from collections.abc import Iterator

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app import store
from app.celery_app import celery_app
from app.settings import settings
from main import app

USER_A_KEY = "default_api_key"
USER_B_KEY = "another_api_key"

# Tasks run inside the request that enqueues them. Results go to files, so
# /task-status can read them back without a broker or Redis. This runs at import,
# before test collection, because Celery reads these settings when it first
# builds a task, and collecting a module that imports a task builds it.
_results_dir = tempfile.TemporaryDirectory(prefix="celery-results-")
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
    task_store_eager_result=True,
    result_backend=f"file://{_results_dir.name}",
)


@pytest.fixture(autouse=True)
def short_stream_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    # A stream that never sees a terminal status fails the test instead of
    # hanging it for the production timeout.
    monkeypatch.setattr(settings, "stream_timeout_s", 5)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.tasks.time.sleep", lambda _: None)


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> fakeredis.FakeRedis:
    fake = fakeredis.FakeRedis(server=fakeredis.FakeServer(), decode_responses=True)
    monkeypatch.setattr(store, "get_redis", lambda: fake)
    return fake


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
