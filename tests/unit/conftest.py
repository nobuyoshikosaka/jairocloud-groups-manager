import typing as t

from pathlib import Path

import pytest

from server import const
from server.config import RuntimeConfig
from server.factory import create_app

if t.TYPE_CHECKING:
    from flask import Flask


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
                "custom_group": "jc_{repository_id}_groups_{custom_id}_test",
            }
        },
        "POSTGRES": {"db": "jctest", "host": db_host},
    })


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
