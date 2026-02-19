import typing as t

from pathlib import Path

import pytest

from server import const
from server.config import RuntimeConfig
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
    redis_host = "redis" if is_running_in_docker() else "localhost"
    amqp_host = "rabbitmq" if is_running_in_docker() else "localhost"
    return RuntimeConfig.model_validate({
        "SECRET_KEY": "test_secret_key",
        "LOG": {
            "level": "INFO",
        },
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
        "REDIS": {
            "cache_type": "RedisCache",
            "single": {"base_url": f"redis://{redis_host}:6379/0"},
            "key_prefix": "jcgroups-test",
        },
        "RABBITMQ": {"url": f"amqp://guest:guest@{amqp_host}:5672//"},
        "SESSION": {"sliding_lifetime": 3600},
    })


@pytest.fixture(autouse=True)
def redis_disable(mocker: MockerFixture):
    mocker.patch("server.datastore.Redis")
    mocker.patch("server.datastore.sentinel")


@pytest.fixture
def datastore(mocker: MockerFixture):
    app_cache = mocker.MagicMock()
    account_store = mocker.MagicMock()
    group_cache = mocker.MagicMock()

    def _stores(name):
        return {
            "app_cache": app_cache,
            "account_store": account_store,
            "group_cache": group_cache,
        }[name]

    mocker.patch("server.datastore._stores", side_effect=_stores)

    return app_cache, account_store, group_cache


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
