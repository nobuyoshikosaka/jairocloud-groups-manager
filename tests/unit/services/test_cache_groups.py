import typing as t

from datetime import UTC, datetime
from unittest.mock import MagicMock, call

from server.api.schemas import CacheQuery
from server.entities.search_request import SearchResult
from server.services.cache_groups import (
    check_updating_cache_is_running,
    get_repository_cache,
    update,
    update_count_signal,
    update_one_task,
    update_result_signal,
    update_run_task,
    update_task,
)


if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_get_repository_cache(mocker: MockerFixture, app, repository_summaries, cache_redis_key, repository_caches):
    with app.app_context():
        query = CacheQuery(l=20, p=1)
        repositories = repository_summaries(20)
        keys = cache_redis_key([repo.service_url.host for repo in repositories.resources[::2]])
        now = datetime.now(UTC)
        caches = repository_caches(repositories.resources, now, True)
        mock_scan = mocker.patch(
            "server.services.cache_groups.group_cache.scan",
            side_effect=[
                (0, keys),
            ],
        )
        mock_hget = mocker.patch(
            "server.services.cache_groups.group_cache.hget",
            return_value=now.isoformat(),
        )

        result = get_repository_cache(repositories, query)
        expect = SearchResult(
            total=20,
            resources=caches,
            page_size=20,
            offset=1,
        )
        assert result == expect
        mock_scan.assert_called()
        assert mock_hget.call_count == 10  # noqa: PLR2004

    mocker.stopall()


def test_get_repository_cache_multi_scan(
    mocker: MockerFixture, app, repository_summaries, cache_redis_key, repository_caches
):
    with app.app_context():
        query = CacheQuery(l=20, p=1)
        repositories = repository_summaries(20)
        keys = cache_redis_key([repo.service_url.host for repo in repositories.resources[::2]])
        now = datetime.now(UTC)
        caches = repository_caches(repositories.resources, now, True)
        mock_scan = mocker.patch(
            "server.services.cache_groups.group_cache.scan",
            side_effect=[
                (1, keys[:10]),
                (0, keys[10:]),
            ],
        )
        mock_hget = mocker.patch(
            "server.services.cache_groups.group_cache.hget",
            return_value=now.isoformat(),
        )

        result = get_repository_cache(repositories, query)
        expect = SearchResult(
            total=20,
            resources=caches,
            page_size=20,
            offset=1,
        )
        assert result == expect
        mock_scan.assert_called()
        assert mock_hget.call_count == 10  # noqa: PLR2004

    mocker.stopall()


def test_get_repository_cache_all_cache_not_exceeding_page_size(
    mocker: MockerFixture, app, repository_summaries, cache_redis_key, repository_caches
):
    with app.app_context():
        query = CacheQuery(f=["cache"], l=20, p=1)
        repositories = repository_summaries(20)
        keys = cache_redis_key([repo.service_url.host for repo in repositories.resources])
        now = datetime.now(UTC)
        caches = repository_caches(repositories.resources, now, False)
        mock_scan = mocker.patch(
            "server.services.cache_groups.group_cache.scan",
            side_effect=[
                (0, keys),
            ],
        )
        mock_hget = mocker.patch(
            "server.services.cache_groups.group_cache.hget",
            return_value=now.isoformat(),
        )

        result = get_repository_cache(repositories, query)
        expect = SearchResult(
            total=20,
            resources=caches,
            page_size=20,
            offset=1,
        )
        assert result == expect
        mock_scan.assert_called()
        assert mock_hget.call_count == 20  # noqa: PLR2004

    mocker.stopall()


def test_get_repository_cache_all_cache_exceeding_page_size(
    mocker: MockerFixture, app, repository_summaries, cache_redis_key, repository_caches
):
    with app.app_context():
        query = CacheQuery(f=["cache"], l=20, p=1)
        repositories = repository_summaries(30)
        keys = cache_redis_key([repo.service_url.host for repo in repositories.resources])
        now = datetime.now(UTC)
        caches = repository_caches(repositories.resources[:20], now, False)
        mock_scan = mocker.patch(
            "server.services.cache_groups.group_cache.scan",
            side_effect=[
                (0, keys),
            ],
        )
        mock_hget = mocker.patch(
            "server.services.cache_groups.group_cache.hget",
            return_value=now.isoformat(),
        )

        result = get_repository_cache(repositories, query)
        expect = SearchResult(
            total=30,
            resources=caches,
            page_size=20,
            offset=1,
        )
        assert result == expect
        mock_scan.assert_called()
        assert mock_hget.call_count == 30  # noqa: PLR2004

    mocker.stopall()


def test_get_repository_cache_all_cache_exceeding_page_size_next_page(
    mocker: MockerFixture, app, repository_summaries, cache_redis_key, repository_caches
):
    with app.app_context():
        query = CacheQuery(f=["cache"], l=20, p=2)
        repositories = repository_summaries(30)
        keys = cache_redis_key([repo.service_url.host for repo in repositories.resources])
        now = datetime.now(UTC)
        caches = repository_caches(repositories.resources[20:30], now, False)
        mock_scan = mocker.patch(
            "server.services.cache_groups.group_cache.scan",
            side_effect=[
                (0, keys),
            ],
        )
        mock_hget = mocker.patch(
            "server.services.cache_groups.group_cache.hget",
            return_value=now.isoformat(),
        )

        result = get_repository_cache(repositories, query)
        expect = SearchResult(
            total=30,
            resources=caches,
            page_size=20,
            offset=21,
        )
        assert result == expect
        mock_scan.assert_called()
        assert mock_hget.call_count == 30  # noqa: PLR2004

    mocker.stopall()


def test_get_repository_cache_empty_cache(mocker: MockerFixture, app, repository_summaries):
    with app.app_context():
        query = CacheQuery(f=["cache"], l=20, p=1)
        repositories = repository_summaries(20)
        now = datetime.now(UTC)
        mock_scan = mocker.patch(
            "server.services.cache_groups.group_cache.scan",
            side_effect=[
                (0, []),
            ],
        )
        mock_hget = mocker.patch(
            "server.services.cache_groups.group_cache.hget",
            return_value=now.isoformat(),
        )

        result = get_repository_cache(repositories, query)
        expect = SearchResult(
            total=0,
            resources=[],
            page_size=20,
            offset=1,
        )
        assert result == expect
        mock_scan.assert_called()
        mock_hget.assert_not_called()

    mocker.stopall()


def test_get_repository_cache_half_cache(
    mocker: MockerFixture, app, repository_summaries, cache_redis_key, repository_caches
):
    with app.app_context():
        query = CacheQuery(f=["cache"], l=20, p=1)
        repositories = repository_summaries(20)
        keys = cache_redis_key([repo.service_url.host for repo in repositories.resources[::2]])
        now = datetime.now(UTC)
        caches = repository_caches(repositories.resources[::2], now, False)
        mock_scan = mocker.patch(
            "server.services.cache_groups.group_cache.scan",
            side_effect=[
                (0, keys),
            ],
        )
        mock_hget = mocker.patch(
            "server.services.cache_groups.group_cache.hget",
            return_value=now.isoformat(),
        )

        result = get_repository_cache(repositories, query)
        expect = SearchResult(
            total=10,
            resources=caches,
            page_size=20,
            offset=1,
        )
        assert result == expect
        mock_scan.assert_called()
        assert mock_hget.call_count == 10  # noqa: PLR2004

    mocker.stopall()


def test_get_repository_cache_no_cache_not_exceeding_page_size(
    mocker: MockerFixture, app, repository_summaries, cache_redis_key, repository_caches
):
    with app.app_context():
        query = CacheQuery(f=["no_cache"], l=20, p=1)
        repositories = repository_summaries(20)
        now = datetime.now(UTC)
        caches = repository_caches(repositories.resources, None, False)
        mock_scan = mocker.patch(
            "server.services.cache_groups.group_cache.scan",
            side_effect=[
                (0, []),
            ],
        )
        mock_hget = mocker.patch(
            "server.services.cache_groups.group_cache.hget",
            return_value=now.isoformat(),
        )

        result = get_repository_cache(repositories, query)
        expect = SearchResult(
            total=20,
            resources=caches,
            page_size=20,
            offset=1,
        )
        assert result == expect
        mock_scan.assert_called()
        mock_hget.assert_not_called()

    mocker.stopall()


def test_get_repository_cache_no_cache_exceeding_page_size(
    mocker: MockerFixture, app, repository_summaries, cache_redis_key, repository_caches
):
    with app.app_context():
        query = CacheQuery(f=["no_cache"], l=20, p=1)
        repositories = repository_summaries(30)
        now = datetime.now(UTC)
        caches = repository_caches(repositories.resources[:20], None, False)
        mock_scan = mocker.patch(
            "server.services.cache_groups.group_cache.scan",
            side_effect=[
                (0, []),
            ],
        )
        mock_hget = mocker.patch(
            "server.services.cache_groups.group_cache.hget",
            return_value=now.isoformat(),
        )

        result = get_repository_cache(repositories, query)
        expect = SearchResult(
            total=30,
            resources=caches,
            page_size=20,
            offset=1,
        )
        assert result == expect
        mock_scan.assert_called()
        mock_hget.assert_not_called()

    mocker.stopall()


def test_get_repository_cache_no_cache_exceeding_page_size_next_page(
    mocker: MockerFixture, app, repository_summaries, cache_redis_key, repository_caches
):
    with app.app_context():
        query = CacheQuery(f=["no_cache"], l=20, p=2)
        repositories = repository_summaries(30)
        now = datetime.now(UTC)
        caches = repository_caches(repositories.resources[20:30], None, False)
        mock_scan = mocker.patch(
            "server.services.cache_groups.group_cache.scan",
            side_effect=[
                (0, []),
            ],
        )
        mock_hget = mocker.patch(
            "server.services.cache_groups.group_cache.hget",
            return_value=now.isoformat(),
        )

        result = get_repository_cache(repositories, query)
        expect = SearchResult(
            total=30,
            resources=caches,
            page_size=20,
            offset=21,
        )
        assert result == expect
        mock_scan.assert_called()
        mock_hget.assert_not_called()

    mocker.stopall()


def test_get_repository_cache_no_cache_all_cache(mocker: MockerFixture, app, repository_summaries, cache_redis_key):
    with app.app_context():
        query = CacheQuery(f=["no_cache"], l=20, p=1)
        now = datetime.now(UTC)
        repositories = repository_summaries(20)
        keys = cache_redis_key([repo.service_url.host for repo in repositories.resources])
        mock_scan = mocker.patch(
            "server.services.cache_groups.group_cache.scan",
            side_effect=[
                (0, keys),
            ],
        )
        mock_hget = mocker.patch(
            "server.services.cache_groups.group_cache.hget",
            return_value=now.isoformat(),
        )

        result = get_repository_cache(repositories, query)
        expect = SearchResult(
            total=0,
            resources=[],
            page_size=20,
            offset=1,
        )
        assert result == expect
        mock_scan.assert_called()
        assert mock_hget.call_count == 20  # noqa: PLR2004

    mocker.stopall()


def test_get_repository_cache_no_cache_half_cache(
    mocker: MockerFixture, app, repository_summaries, cache_redis_key, repository_caches
):
    with app.app_context():
        query = CacheQuery(f=["no_cache"], l=20, p=1)
        repositories = repository_summaries(20)
        keys = cache_redis_key([repo.service_url.host for repo in repositories.resources[::2]])
        now = datetime.now(UTC)
        caches = repository_caches(repositories.resources[1::2], None, False)
        mock_scan = mocker.patch(
            "server.services.cache_groups.group_cache.scan",
            side_effect=[
                (0, keys),
            ],
        )
        mock_hget = mocker.patch(
            "server.services.cache_groups.group_cache.hget",
            return_value=now.isoformat(),
        )

        result = get_repository_cache(repositories, query)
        expect = SearchResult(
            total=10,
            resources=caches,
            page_size=20,
            offset=1,
        )
        assert result == expect
        mock_scan.assert_called()
        assert mock_hget.call_count == 10  # noqa: PLR2004

    mocker.stopall()


def test_update(mocker: MockerFixture, app):
    with app.app_context():
        mock_check = mocker.patch(
            "server.services.cache_groups.check_updating_cache_is_running",
            return_value=False,
        )
        mock_update_task = mocker.patch(
            "server.services.cache_groups.update_task.apply_async",
        )

        fqdn_list = ["example.com"]
        op = "all"
        update(fqdn_list, op)

        mock_check.assert_called_once()
        mock_update_task.assert_called_once_with(fqdn_list, op)

    mocker.stopall()


def test_update_raises_runtime_error_when_task_running(mocker: MockerFixture, app):
    with app.app_context():
        mock_check = mocker.patch(
            "server.services.cache_groups.check_updating_cache_is_running",
            return_value=True,
        )
        mock_update_task = mocker.patch(
            "server.services.cache_groups.update_task.apply_async",
        )
        fqdn_list = ["example.com"]
        op = "all"

        try:
            update(fqdn_list, op)
        except RuntimeError as e:
            assert str(e) == "A cache update task is already running."

        mock_check.assert_called_once()
        mock_update_task.assert_not_called()

    mocker.stopall()


def test_update_task_all(mocker: MockerFixture, app):
    with app.app_context():
        mock_update_all_caches = mocker.patch(
            "server.services.cache_groups.update_run_task",
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        fqdn_list = ["example.com"]
        op = "all"

        update_task(fqdn_list, op)  # pyright: ignore[reportArgumentType]

        mock_update_all_caches.assert_called_once()
        mock_hset.assert_not_called()

    mocker.stopall()


def test_update_task_all_count_signal_once(mocker: MockerFixture, app):
    with app.app_context():
        mock_update_all_caches = mocker.patch(
            "server.services.cache_groups.update_run_task",
            side_effect=lambda: update_count_signal.send(
                None,
                total=100,
                done=50,
                current="example.com",
            ),
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        fqdn_list = ["example.com"]
        op = "all"

        update_task(fqdn_list, op)  # pyright: ignore[reportArgumentType]

        # Simulate sending the update count signal

        mock_update_all_caches.assert_called_once()
        mock_hset.assert_called_with(
            "jcgroups_cache",
            mapping={
                "total": 100,
                "done": 50,
                "current": "example.com",
            },
        )

    mocker.stopall()


def test_update_task_all_result_signal_once(mocker: MockerFixture, app):
    with app.app_context():
        now = datetime.now(UTC)
        mock_update_all_caches = mocker.patch(
            "server.services.cache_groups.update_run_task",
            side_effect=lambda: update_result_signal.send(
                None,
                task_name="example_com_0",
                status="success",
                code="",
                updated=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        fqdn_list = ["example.com"]
        op = "all"

        update_task(fqdn_list, op)  # pyright: ignore[reportArgumentType]

        # Simulate sending the update result signal

        mock_update_all_caches.assert_called_once()
        mock_hset.assert_called_with(
            "jcgroups_cache",
            mapping={
                "example_com_0": "{'status': 'success', 'code': '', 'updated': '"
                + now.strftime("%Y-%m-%dT%H:%M:%SZ")
                + "'}"
            },
        )

    mocker.stopall()


def test_update_task_all_signals_once(mocker: MockerFixture, app):
    with app.app_context():
        now = datetime.now(UTC)

        def side_effect():
            update_count_signal.send(
                None,
                total=100,
                done=50,
                current="example.com",
            )
            update_result_signal.send(
                None,
                task_name="example_com_0",
                status="success",
                code="",
                updated=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

        mock_update_all_caches = mocker.patch(
            "server.services.cache_groups.update_run_task",
            side_effect=side_effect,
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        fqdn_list = ["example.com"]
        op = "all"

        update_task(fqdn_list, op)  # pyright: ignore[reportArgumentType]

        # Simulate sending the update count and result signals

        mock_update_all_caches.assert_called_once()
        expected_calls = [
            call(
                "jcgroups_cache",
                mapping={
                    "total": 100,
                    "done": 50,
                    "current": "example.com",
                },
            ),
            call(
                "jcgroups_cache",
                mapping={
                    "example_com_0": "{'status': 'success', 'code': '', 'updated': '"
                    + now.strftime("%Y-%m-%dT%H:%M:%SZ")
                    + "'}"
                },
            ),
        ]
        mock_hset.assert_has_calls(expected_calls, any_order=False)

    mocker.stopall()


def test_update_task_all_signal_multiple(mocker: MockerFixture, app):
    with app.app_context():
        now = datetime.now(UTC)

        def side_effect():
            for i in range(3):
                update_count_signal.send(
                    None,
                    total=100,
                    done=50 + i,
                    current=f"example{i}.com",
                )
                update_result_signal.send(
                    None,
                    task_name=f"example_com_{i}",
                    status="success",
                    code="",
                    updated=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )

        mock_update_all_caches = mocker.patch(
            "server.services.cache_groups.update_run_task",
            side_effect=side_effect,
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        fqdn_list = ["example.com"]
        op = "all"

        update_task(fqdn_list, op)  # pyright: ignore[reportArgumentType]

        # Simulate sending the update count and result signals multiple times

        mock_update_all_caches.assert_called_once()
        expected_calls = [
            call(
                "jcgroups_cache",
                mapping={
                    "total": 100,
                    "done": 50 + i,
                    "current": f"example{i}.com",
                },
            )
            for i in range(3)
        ] + [
            call(
                "jcgroups_cache",
                mapping={
                    f"example_com_{i}": "{'status': 'success', 'code': '', 'updated': '"
                    + now.strftime("%Y-%m-%dT%H:%M:%SZ")
                    + "'}"
                },
            )
            for i in range(3)
        ]
        mock_hset.assert_has_calls(expected_calls, any_order=True)

    mocker.stopall()


def test_update_task_specified(mocker: MockerFixture, app):
    with app.app_context():
        mock_update_specified_caches = mocker.patch(
            "server.services.cache_groups.update_one_task",
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        fqdn_list = ["example.com"]
        op = "id-specified"

        update_task(fqdn_list, op)  # pyright: ignore[reportArgumentType]

        mock_update_specified_caches.assert_called_once_with(fqdn_list)
        mock_hset.assert_not_called()

    mocker.stopall()


def test_update_task_specified_count_signal_once(mocker: MockerFixture, app):
    with app.app_context():
        mock_update_specified_caches = mocker.patch(
            "server.services.cache_groups.update_one_task",
            side_effect=lambda *_, **__: update_count_signal.send(
                None,
                total=100,
                done=50,
                current="example.com",
            ),
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        fqdn_list = ["example.com"]
        op = "id-specified"

        update_task(fqdn_list, op)  # pyright: ignore[reportArgumentType]

        # Simulate sending the update count signal

        mock_update_specified_caches.assert_called_once_with(fqdn_list)
        mock_hset.assert_called_with(
            "jcgroups_cache",
            mapping={
                "total": 100,
                "done": 50,
                "current": "example.com",
            },
        )

    mocker.stopall()


def test_update_task_specified_result_signal_once(mocker: MockerFixture, app):
    with app.app_context():
        now = datetime.now(UTC)
        mock_update_specified_caches = mocker.patch(
            "server.services.cache_groups.update_one_task",
            side_effect=lambda *_, **__: update_result_signal.send(
                None,
                task_name="example_com_0",
                status="success",
                code="",
                updated=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        fqdn_list = ["example.com"]
        op = "id-specified"

        update_task(fqdn_list, op)  # pyright: ignore[reportArgumentType]

        # Simulate sending the update result signal

        mock_update_specified_caches.assert_called_once_with(fqdn_list)
        mock_hset.assert_called_with(
            "jcgroups_cache",
            mapping={
                "example_com_0": "{'status': 'success', 'code': '', 'updated': '"
                + now.strftime("%Y-%m-%dT%H:%M:%SZ")
                + "'}"
            },
        )

    mocker.stopall()


def test_update_task_specified_signals_once(mocker: MockerFixture, app):
    with app.app_context():
        now = datetime.now(UTC)

        def side_effect(*_, **__):
            update_count_signal.send(
                None,
                total=100,
                done=50,
                current="example.com",
            )
            update_result_signal.send(
                None,
                task_name="example_com_0",
                status="success",
                code="",
                updated=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

        mock_update_specified_caches = mocker.patch(
            "server.services.cache_groups.update_one_task",
            side_effect=side_effect,
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        fqdn_list = ["example.com"]
        op = "id-specified"

        update_task(fqdn_list, op)  # pyright: ignore[reportArgumentType]

        # Simulate sending the update count and result signals

        mock_update_specified_caches.assert_called_once_with(fqdn_list)
        expected_calls = [
            call(
                "jcgroups_cache",
                mapping={
                    "total": 100,
                    "done": 50,
                    "current": "example.com",
                },
            ),
            call(
                "jcgroups_cache",
                mapping={
                    "example_com_0": "{'status': 'success', 'code': '', 'updated': '"
                    + now.strftime("%Y-%m-%dT%H:%M:%SZ")
                    + "'}"
                },
            ),
        ]
        mock_hset.assert_has_calls(expected_calls, any_order=False)

    mocker.stopall()


def test_update_task_specified_signal_multiple(mocker: MockerFixture, app):
    with app.app_context():
        now = datetime.now(UTC)

        def side_effect(*_, **__):
            for i in range(3):
                update_count_signal.send(
                    None,
                    total=100,
                    done=50 + i,
                    current=f"example{i}.com",
                )
                update_result_signal.send(
                    None,
                    task_name=f"example_com_{i}",
                    status="success",
                    code="",
                    updated=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )

        mock_update_specified_caches = mocker.patch(
            "server.services.cache_groups.update_one_task",
            side_effect=side_effect,
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        fqdn_list = ["example.com"]
        op = "id-specified"

        update_task(fqdn_list, op)  # pyright: ignore[reportArgumentType]

        # Simulate sending the update count and result signals multiple times

        mock_update_specified_caches.assert_called_once_with(fqdn_list)
        expected_calls = [
            call(
                "jcgroups_cache",
                mapping={
                    "total": 100,
                    "done": 50 + i,
                    "current": f"example{i}.com",
                },
            )
            for i in range(3)
        ] + [
            call(
                "jcgroups_cache",
                mapping={
                    f"example_com_{i}": "{'status': 'success', 'code': '', 'updated': '"
                    + now.strftime("%Y-%m-%dT%H:%M:%SZ")
                    + "'}"
                },
            )
            for i in range(3)
        ]
        mock_hset.assert_has_calls(expected_calls, any_order=True)

    mocker.stopall()


def test_update_run_task_toml_path(mocker: MockerFixture, app):
    with app.app_context():
        mock_fetch_all = mocker.patch(
            "server.services.cache_groups.fetch_all",
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        mocker.patch(
            "server.services.cache_groups.config",
            CACHE_GROUPS=MagicMock(
                cache_redis_key="{prefix}cache",
                toml_path="/path/to/toml",
                directory_path="",
                fqdn_list_file="",
            ),
            REDIS=MagicMock(key_prefix="jcgroups_"),
        )

        update_run_task()

        mock_fetch_all.assert_called_once_with(toml_path="/path/to/toml")
        mock_hset.assert_called_once_with(
            "jcgroups_cache",
            mapping={"total": "", "done": 0, "current": ""},
        )

    mocker.stopall()


def test_update_run_task_not_toml_path(mocker: MockerFixture, app):
    with app.app_context():
        mock_fetch_all = mocker.patch(
            "server.services.cache_groups.fetch_all",
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        mocker.patch(
            "server.services.cache_groups.config",
            CACHE_GROUPS=MagicMock(
                cache_redis_key="{prefix}cache",
                toml_path="",
                directory_path="./cache_db/tls",
                fqdn_list_file="fqdn_list.toml",
            ),
            REDIS=MagicMock(key_prefix="jcgroups_"),
        )

        update_run_task()

        mock_fetch_all.assert_called_once_with(
            directory_path="./cache_db/tls",
            fqdn_list_file="fqdn_list.toml",
        )
        mock_hset.assert_called_once_with(
            "jcgroups_cache",
            mapping={"total": "", "done": 0, "current": ""},
        )

    mocker.stopall()


def test_update_run_task_all_settings(mocker: MockerFixture, app):
    with app.app_context():
        mock_fetch_all = mocker.patch(
            "server.services.cache_groups.fetch_all",
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        mocker.patch(
            "server.services.cache_groups.config",
            CACHE_GROUPS=MagicMock(
                cache_redis_key="{prefix}cache",
                toml_path="/path/to/toml",
                directory_path="./cache_db/tls",
                fqdn_list_file="fqdn_list.toml",
            ),
            REDIS=MagicMock(key_prefix="jcgroups_"),
        )

        update_run_task()

        mock_fetch_all.assert_called_once_with(
            toml_path="/path/to/toml",
        )
        mock_hset.assert_called_once_with(
            "jcgroups_cache",
            mapping={"total": "", "done": 0, "current": ""},
        )

    mocker.stopall()


def test_update_one_task_toml_path(mocker: MockerFixture, app):
    with app.app_context():
        mock_fetch_one = mocker.patch(
            "server.services.cache_groups.fetch_one",
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        mocker.patch(
            "server.services.cache_groups.config",
            CACHE_GROUPS=MagicMock(
                cache_redis_key="{prefix}cache",
                toml_path="/path/to/toml",
                directory_path="",
                fqdn_list_file="",
            ),
            REDIS=MagicMock(key_prefix="jcgroups_"),
        )
        fqdn_list = ["example.com"]

        update_one_task(fqdn_list)

        mock_fetch_one.assert_called_once_with("example.com", toml_path="/path/to/toml")
        assert mock_hset.call_args_list == [
            call(
                "jcgroups_cache",
                mapping={"total": 1, "done": 0, "current": ""},
            ),
            call(
                "jcgroups_cache",
                mapping={"done": 1, "current": "example.com"},
            ),
        ]

    mocker.stopall()


def test_update_one_task_not_toml_path(mocker: MockerFixture, app):
    with app.app_context():
        mock_fetch_one = mocker.patch(
            "server.services.cache_groups.fetch_one",
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        mocker.patch(
            "server.services.cache_groups.config",
            CACHE_GROUPS=MagicMock(
                cache_redis_key="{prefix}cache",
                toml_path="",
                directory_path="./cache_db/tls",
                fqdn_list_file="fqdn_list.toml",
            ),
            REDIS=MagicMock(key_prefix="jcgroups_"),
        )
        fqdn_list = ["example.com"]

        update_one_task(fqdn_list)

        mock_fetch_one.assert_called_once_with(
            "example.com",
            directory_path="./cache_db/tls",
            fqdn_list_file="fqdn_list.toml",
        )
        assert mock_hset.call_args_list == [
            call(
                "jcgroups_cache",
                mapping={"total": 1, "done": 0, "current": ""},
            ),
            call(
                "jcgroups_cache",
                mapping={"done": 1, "current": "example.com"},
            ),
        ]

    mocker.stopall()


def test_update_one_task_all_settings(mocker: MockerFixture, app):
    with app.app_context():
        mock_fetch_one = mocker.patch(
            "server.services.cache_groups.fetch_one",
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        mocker.patch(
            "server.services.cache_groups.config",
            CACHE_GROUPS=MagicMock(
                cache_redis_key="{prefix}cache",
                toml_path="/path/to/toml",
                directory_path="./cache_db/tls",
                fqdn_list_file="fqdn_list.toml",
            ),
            REDIS=MagicMock(key_prefix="jcgroups_"),
        )
        fqdn_list = ["example.com"]

        update_one_task(fqdn_list)

        mock_fetch_one.assert_called_once_with("example.com", toml_path="/path/to/toml")
        assert mock_hset.call_args_list == [
            call(
                "jcgroups_cache",
                mapping={"total": 1, "done": 0, "current": ""},
            ),
            call(
                "jcgroups_cache",
                mapping={"done": 1, "current": "example.com"},
            ),
        ]

    mocker.stopall()


def test_update_one_task_multi_repositories(mocker: MockerFixture, app):
    with app.app_context():
        mock_fetch_one = mocker.patch(
            "server.services.cache_groups.fetch_one",
        )
        mock_hset = mocker.patch(
            "server.services.cache_groups.app_cache.hset",
        )
        mocker.patch(
            "server.services.cache_groups.config",
            CACHE_GROUPS=MagicMock(
                cache_redis_key="{prefix}cache",
                toml_path="/path/to/toml",
                directory_path="./cache_db/tls",
                fqdn_list_file="fqdn_list.toml",
            ),
            REDIS=MagicMock(key_prefix="jcgroups_"),
        )
        fqdn_list = ["example1.com", "example2.com", "example3.com"]

        update_one_task(fqdn_list)

        assert mock_fetch_one.call_count == 3
        expected_calls = [
            call(
                "jcgroups_cache",
                mapping={"total": 3, "done": 0, "current": ""},
            ),
            call(
                "jcgroups_cache",
                mapping={"done": 1, "current": "example1.com"},
            ),
            call(
                "jcgroups_cache",
                mapping={"done": 2, "current": "example2.com"},
            ),
            call(
                "jcgroups_cache",
                mapping={"done": 3, "current": "example3.com"},
            ),
        ]
        mock_hset.assert_has_calls(expected_calls, any_order=False)

    mocker.stopall()


def test_check_updating_cache_is_running_exists(mocker: MockerFixture, app):
    with app.app_context():
        mock_get = mocker.patch(
            "server.services.cache_groups.app_cache.exists",
            return_value=True,
        )

        result = check_updating_cache_is_running()
        assert result is True
        mock_get.assert_called_once_with("jcgroups_cache")

    mocker.stopall()


def test_check_updating_cache_is_running_not_exists(mocker: MockerFixture, app):
    with app.app_context():
        mock_get = mocker.patch(
            "server.services.cache_groups.app_cache.exists",
            return_value=False,
        )

        result = check_updating_cache_is_running()
        assert result is False
        mock_get.assert_called_once_with("jcgroups_cache")

    mocker.stopall()
