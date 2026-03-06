import inspect
import typing as t

from datetime import datetime
from pathlib import Path

import pytest

from pydantic import HttpUrl

from server import const
from server.config import RuntimeConfig
from server.entities.cache import RepositoryCache
from server.entities.search_request import SearchResult
from server.entities.summaries import RepositorySummary
from server.factory import create_app


if t.TYPE_CHECKING:
    from flask import Flask
    from pytest_mock import MockerFixture


def is_running_in_docker() -> bool:
    return Path("/.dockerenv").exists()


@pytest.fixture(autouse=True)
def set_test_constants():
    const.MAP_USER_SCHEMA = "urn:ietf:params:scim:schemas:mace:example.jp:core:2.0:User"
    const.MAP_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:mace:example.jp:core:2.0:Group"
    const.MAP_SERVICE_SCHEMA = "urn:ietf:params:scim:schemas:mace:example.jp:core:2.0:Service"


@pytest.fixture
def instance_path(tmp_path: Path) -> Path:
    return tmp_path / "instance"


@pytest.fixture
def test_config():
    db_host = "postgres" if is_running_in_docker() else "localhost"
    return RuntimeConfig.model_validate({
        "SECRET_KEY": "test_secret_key",
        "SP": {
            "entity_id": "https://test/shibboleth-sp",
            "crt": "/test/server.crt",
            "key": "/test/server.key",
        },
        "MAP_CORE": {
            "base_url": "https://mapcore.test.jp",
            "timeout": 3,
        },
        "REPOSITORIES": {
            "id_patterns": {
                "sp_connecter": "jc_{repository_id}_test",
            },
        },
        "GROUPS": {
            "id_patterns": {
                "system_admin": "jc_roles_sysadm_test",
                "repository_admin": "jc_{repository_id}_roles_repoadm_test",
                "community_admin": "jc_{repository_id}_roles_comadm_test",
                "contributor": "jc_{repository_id}_roles_contributor_test",
                "general_user": "jc_{repository_id}_roles_generaluser_test",
                "user_defined": "jc_{repository_id}_groups_{user_defined_id}_test",
            }
        },
        "POSTGRES": {"db": "jctest", "host": db_host},
        "LOG": {"level": "DEBUG"},
        "REDIS": {
            "single": {
                "base_url": "redis://redis-single:6379",
            },
            "sentinel": {
                "sentinels": [
                    {
                        "host": "",
                        "port": 26379,
                    }
                ]
            },
        },
        "RABBITMQ": {
            "url": "amqp://guest:guest@rabbitmq:5672//",
        },
        "CACHE_GROUPS": {
            "cache_redis_key": "{prefix}cache",
            "gakunin_redis_key": "{fqdn}_gakunin_groups",
            "map_groups_api_endpoint": "https://sample.gakunin.jp/api/groups/",
            "toml_path": "cache_db_config.toml",
            "directory_path": "./cache_db/tls",
            "fqdn_list_file": "fqdn_list.toml",
        },
    })


@pytest.fixture(autouse=True)
def mock_redis(mocker: MockerFixture):
    mock_redis = mocker.patch("server.datastore.Redis")
    mock_redis_instance = mock_redis.from_url.return_value
    mock_redis_instance.ping.return_value = True
    return mock_redis_instance


@pytest.fixture
def unwrap():
    def _unwrap(f: t.Callable) -> t.Callable:
        return inspect.unwrap(f)

    return _unwrap


@pytest.fixture
def base_app(instance_path, test_config):
    app = create_app(__name__, config=test_config)
    app.instance_path = instance_path
    app.config["TESTING"] = True

    return app


@pytest.fixture
def app(base_app: Flask):
    with base_app.app_context():
        yield base_app


@pytest.fixture
def repository_summaries():
    def _data(num: int) -> SearchResult[RepositorySummary]:
        return SearchResult(
            resources=[
                RepositorySummary(
                    id=f"repo_{i}",
                    display_name=f"Repository {i}",
                    service_url=HttpUrl(f"https://repo{i}.example.jp"),
                    sp_connector_id=f"jc_repo_{i}_sp",
                )
                for i in range(1, num + 1)
            ],
            total=num,
            page_size=20,
            offset=1,
        )

    return _data


@pytest.fixture
def cache_redis_key():
    def _keys(fqdn_list: list[str]) -> list[bytes]:
        return [f"{fqdn.replace('-', '_').replace('.', '_')}_gakunin_groups".encode() for fqdn in fqdn_list]

    return _keys


@pytest.fixture
def repository_caches():
    def _data(repositories: list[RepositorySummary], now: datetime, every_other: bool) -> list[RepositoryCache]:
        return [
            RepositoryCache(
                id=repositories[i].id,
                name=repositories[i].display_name,  # pyright: ignore[reportArgumentType],
                url=str(repositories[i].service_url),
                updated=now if not every_other or i % 2 == 0 else None,
            )
            for i in range(len(repositories))
        ]

    return _data
