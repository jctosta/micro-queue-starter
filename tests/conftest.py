from collections.abc import Iterator

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app import store
from app.celery_app import celery_app
from main import app

USER_A_KEY = "default_api_key"
USER_B_KEY = "another_api_key"


@pytest.fixture(scope="session", autouse=True)
def eager_celery(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Tasks run inside the request that enqueues them. Results go to files, so
    # /task-status can read them back without a broker or Redis.
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        task_store_eager_result=True,
        result_backend=f"file://{tmp_path_factory.mktemp('celery-results')}",
    )


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
