import typing as t

import pytest

from pydantic import BaseModel
from src.server.clients import decoraters
from src.server.entities.map_error import MapError

from server.clients.decoraters import cache_resource, clear_cache


if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture


class DummyModel(BaseModel):
    value: int = 0


def test_cache_resource_with_callable(app, mocker: MockerFixture) -> None:
    ex_num = 11
    app_cache_mock = mocker.patch("server.clients.decoraters.app_cache", new_callable=mocker.MagicMock)
    app_cache_mock.get.return_value = None

    dummy_json = DummyModel(value=ex_num).model_dump_json()
    app_cache_mock.get.side_effect = [None, dummy_json]
    mocker.patch("server.clients.decoraters.config.REDIS.key_prefix", "prefix")
    mocker.patch("server.clients.decoraters.config.REDIS.cache_timeout", 10)

    call_count = {"count": 0}

    def func(x: int) -> DummyModel:
        call_count["count"] += 1
        return DummyModel(value=x + 1)

    decorated = cache_resource(func)
    assert decorated(10).value == ex_num
    assert decorated(10).value == ex_num
    assert call_count["count"] == 1
    assert hasattr(decorated, "_import_name")
    assert hasattr(decorated, "clear_cache")


def test_cache_resource_func_raises(app, mocker: MockerFixture) -> None:
    """Tests that cache_resource propagates exceptions from the wrapped function."""
    ex_str = "fail"
    app_cache_mock = mocker.patch("server.clients.decoraters.app_cache", new_callable=mocker.MagicMock)
    app_cache_mock.get.return_value = None
    mocker.patch("server.clients.decoraters.config.REDIS.key_prefix", "prefix")
    mocker.patch("server.clients.decoraters.config.REDIS.cache_timeout", 10)

    def func(x: int) -> DummyModel:
        raise ValueError(ex_str)

    decorated = cache_resource(func)
    with pytest.raises(ValueError, match=ex_str):
        decorated(1)


def test_cache_resource_maperror_timeout(app, mocker: MockerFixture) -> None:
    ex_num = 10
    app_cache_mock = mocker.patch("server.clients.decoraters.app_cache", new_callable=mocker.MagicMock)
    app_cache_mock.get.return_value = None
    mocker.patch("server.clients.decoraters.config.REDIS.key_prefix", "prefix")
    mocker.patch("server.clients.decoraters.config.REDIS.cache_timeout", ex_num)

    class FakeMapError(BaseModel):
        pass

    def func(x: int) -> FakeMapError:
        return FakeMapError()

    decorated = cache_resource(func)
    decorated(1)
    called_args = app_cache_mock.setex.call_args[0]
    assert called_args[1] == ex_num


def test_cache_resource_sets_timeout_3_on_maperror(app, mocker: MockerFixture) -> None:
    """Tests cache_resource sets timeout=3 when result is MapError."""
    expected_value = 3

    app_cache_mock = mocker.patch("src.server.clients.decoraters.app_cache", new=mocker.MagicMock())
    mocker.patch.object(decoraters.config.REDIS, "cache_timeout", None)
    app_cache_mock.get.return_value = None

    def func(resource_id: str) -> MapError:
        return MapError(status="400", scim_type="invalidFilter", detail="error detail")

    decorated = decoraters.cache_resource(timeout=0)(func)
    result = decorated("abc")
    assert isinstance(result, MapError)
    app_cache_mock.setex.assert_called()
    args, _ = app_cache_mock.setex.call_args
    assert args[1] == expected_value


def test_clear_cache_normal(app, mocker: MockerFixture) -> None:
    """Tests that clear_cache deletes cache keys for given resource_id."""
    scan_keys = [b"prefix:mod.func:1:abc"]

    def dummy_func() -> DummyModel:
        return DummyModel(value=0)

    decorated = cache_resource(dummy_func)
    app_cache_mock = mocker.patch("server.clients.decoraters.app_cache", new=mocker.MagicMock())
    app_cache_mock.get.return_value = None
    app_cache_mock.scan.side_effect = [(1, scan_keys), (0, [])]

    mocker.patch("server.clients.decoraters.config.REDIS.key_prefix", "prefix")

    clear_cache(decorated, "1")
    app_cache_mock.delete.assert_called_with(*scan_keys)


def test_clear_cache_not_decorated(app, mocker: MockerFixture) -> None:
    """Tests that clear_cache raises ValueError if function is not decorated."""

    error_msg = "Function is not decorated with @response_cache."
    mocker.patch("server.clients.decoraters.config.REDIS.key_prefix", "prefix")

    def dummy_func(x):
        return x

    with pytest.raises(ValueError, match=error_msg):
        clear_cache(dummy_func, "1")


def test_cache_resource_timeout_none(app, mocker: MockerFixture) -> None:
    """Tests cache_resource when timeout is None and result is not MapError."""
    expected_value = 42

    def func(resource_id: str) -> DummyModel:
        return DummyModel(value=expected_value)

    mocker.patch.object(decoraters.config.REDIS, "cache_timeout", 99)
    app_cache_mock = mocker.patch("src.server.clients.decoraters.app_cache", new=mocker.MagicMock())
    dummy_json = DummyModel(value=expected_value).model_dump_json()
    app_cache_mock.get.side_effect = [None, dummy_json.encode("utf-8")]

    decorated = decoraters.cache_resource(timeout=None)(func)
    result = decorated("abc")
    assert result.value == expected_value
    app_cache_mock.setex.assert_called_with(mocker.ANY, 99, result.model_dump_json())


def test_cache_resource_result_maperror_sets_timeout(app, mocker: MockerFixture) -> None:
    """Tests cache_resource when result is MapError, timeout is set to 3."""

    def func(resource_id: str) -> MapError:
        return MapError(status="400", scim_type="invalidFilter", detail="error detail")

    mocker.patch.object(decoraters.config.REDIS, "cache_timeout", 99)
    app_cache_mock = mocker.patch("src.server.clients.decoraters.app_cache", new=mocker.MagicMock())
    app_cache_mock.get.return_value = None

    decorated = decoraters.cache_resource(timeout=None)(func)
    result = decorated("abc")
    assert isinstance(result, MapError)


def test_cache_resource_args_empty(app, mocker: MockerFixture) -> None:
    """Tests cache_resource when args is empty (should call original function directly)."""
    called = {}
    expected_value = 42

    def func() -> DummyModel:
        called["ok"] = True
        return DummyModel(value=expected_value)

    decorated = cache_resource(func)
    result = decorated()
    assert result.value == expected_value
    assert called["ok"] is True


def test_clear_cache_scan_loop_keys(app, mocker: MockerFixture) -> None:
    """Tests clear_cache scan loop with keys found and deleted."""
    app_cache_mock = mocker.patch("src.server.clients.decoraters.app_cache", new=mocker.MagicMock())
    scan_results = [("1", ["k1", "k2"]), (0, [])]
    scan_index = {"i": 0}

    def scan_side_effect(*_, **__):
        i = scan_index["i"]
        if i < len(scan_results):
            result = scan_results[i]
            scan_index["i"] += 1
            return result
        return (0, [])

    app_cache_mock.scan.side_effect = scan_side_effect
    app_cache_mock.delete = mocker.MagicMock()

    def dummy_func() -> DummyModel:
        return DummyModel(value=0)

    decorated = cache_resource(dummy_func)

    resource_id = ["id1"]
    decoraters.clear_cache(decorated, *resource_id)
    app_cache_mock.scan.assert_called()
    app_cache_mock.delete.assert_called_with("k1", "k2")


def test_clear_cache_empty_resource_id(app, mocker: MockerFixture) -> None:
    """Tests clear_cache when resource_id is empty (should not scan/delete)."""
    mock_cache = mocker.patch("src.server.clients.decoraters.app_cache", new=mocker.MagicMock())
    mock_cache.scan.side_effect = [(0, [])]
    mock_cache.delete = mocker.MagicMock()

    def dummy_func() -> DummyModel:
        return DummyModel(value=0)

    decorated = cache_resource(dummy_func)

    clear_cache(decorated)
    mock_cache.scan.assert_not_called()
    mock_cache.delete.assert_not_called()
