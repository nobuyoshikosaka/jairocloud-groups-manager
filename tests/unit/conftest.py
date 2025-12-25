import typing as t

from pathlib import Path

import pytest

from sqlalchemy_utils import create_database, database_exists

from server import const
from server.config import PostgresConfig, RuntimeConfig
from server.db.base import db as db_
from server.factory import create_app

if t.TYPE_CHECKING:
    from flask import Flask


def is_running_in_docker() -> bool:
    try:
        with Path("/.dockerenv").open(encoding="utf-8"):
            return True
    except FileNotFoundError:
        return False


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
    return RuntimeConfig(
        SECRET_KEY="test_secret_key",
        POSTGRES=PostgresConfig(db="jctest", host=db_host),
    )


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
def db(app):
    url = app.config["SQLALCHEMY_DATABASE_URI"]
    if not database_exists(url):
        create_database(url)
    else:
        db_.drop_all()
    db_.create_all()

    yield db_

    db_.session.remove()
    db_.drop_all()
