import typing as t

from copy import deepcopy
from datetime import datetime
from unittest.mock import call

from server.api import cache_groups
from server.api.schemas import CacheQuery, CacheRequest, RepositoriesQuery
from server.entities.cache import CacheResult, RepositoryCache, TaskDetail
from server.entities.search_request import SearchResult


if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_get(mocker: MockerFixture, repository_summaries, repository_caches, app, unwrap):
    repositories = repository_summaries(20)
    search_result = SearchResult(
        resources=repository_caches(repositories.resources, None, False),
        total=20,
        page_size=20,
        offset=1,
    )
    mock_search = mocker.patch(
        "server.api.cache_groups.search",
        return_value=repositories,
    )
    mock_get_repository_cache = mocker.patch(
        "server.api.cache_groups.get_repository_cache",
        return_value=search_result,
    )
    with app.test_request_context():
        result = unwrap(cache_groups.get)(CacheQuery(q=None, p=1, l=20, f=[]))

    assert result == search_result
    mock_search.assert_called_once_with(RepositoriesQuery(q=None, k="id", d="asc", p=1, l=20))
    mock_get_repository_cache.assert_called_once_with(repositories, CacheQuery(q=None, p=1, l=20, f=[]))


def test_post(mocker: MockerFixture, app, unwrap):
    mock_update = mocker.patch("server.api.cache_groups.update")
    fqdn_list = ["repo1.example.jp", "repo2.example.jp"]
    operation = "all"
    with app.test_request_context():
        result = unwrap(cache_groups.post)(body=CacheRequest(fqdn_list=fqdn_list, op=operation))

    assert result == "Success"
    mock_update.assert_called_once_with(fqdn_list, operation)


def test_get_task_status_no_task(mocker: MockerFixture, app, unwrap):
    mock_hgetall = mocker.patch("server.api.cache_groups.app_cache.hgetall", return_value={})
    mock_delete = mocker.patch("server.api.cache_groups.app_cache.delete")
    mock_search = mocker.patch("server.api.cache_groups.search")

    with app.test_request_context():
        result = unwrap(cache_groups.get_task_status)()

    assert result == TaskDetail(results=[], current="", total=0, done=0)
    mock_hgetall.assert_called_once_with("jcgroups_cache")
    mock_delete.assert_not_called()
    mock_search.assert_not_called()

    mocker.stopall()


def test_get_task_status_running(mocker: MockerFixture, app, unwrap, repository_summaries):
    task_data = {
        b"current": b"repo1.example.jp",
        b"done": b"5",
        b"total": b"10",
        b"repo1.example.jp_0": b"{'status': 'success', 'updated': '2026-01-01T00:00:00Z'}",
    }
    mock_hgetall = mocker.patch("server.api.cache_groups.app_cache.hgetall", return_value=task_data)
    mock_delete = mocker.patch("server.api.cache_groups.app_cache.delete")
    mock_search = mocker.patch("server.api.cache_groups.search", return_value=repository_summaries(1))

    expect_result = [
        CacheResult(
            type="cache",
            fqdn="repo1.example.jp",
            status="success",
            code=None,
            repository_cached=RepositoryCache(
                id="repo_1",
                name="Repository 1",
                url="https://repo1.example.jp/",
                updated=datetime(2026, 1, 1, 0, 0),  # noqa: DTZ001
            ),
        )
    ]

    with app.test_request_context():
        result = unwrap(cache_groups.get_task_status)()

    assert result == TaskDetail(results=expect_result, current="repo1.example.jp", total=10, done=5)
    mock_hgetall.assert_called_once_with("jcgroups_cache")
    mock_delete.assert_not_called()
    mock_search.assert_called_once_with(
        RepositoriesQuery(
            q="/repo1.example.jp/",
            k="id",
            d="asc",
            p=-1,
            l=1,
        )
    )

    mocker.stopall()


def test_get_task_status_completed(mocker: MockerFixture, app, unwrap, repository_summaries):
    task_data = {
        b"current": b"repo1.example.jp",
        b"done": b"10",
        b"total": b"10",
        b"repo1.example.jp_0": b"{'status': 'success', 'updated': '2026-01-01T00:00:00Z'}",
    }
    mock_hgetall = mocker.patch("server.api.cache_groups.app_cache.hgetall", return_value=task_data)
    mock_delete = mocker.patch("server.api.cache_groups.app_cache.delete")
    mock_search = mocker.patch("server.api.cache_groups.search", return_value=repository_summaries(1))

    expect_result = [
        CacheResult(
            type="cache",
            fqdn="repo1.example.jp",
            status="success",
            code=None,
            repository_cached=RepositoryCache(
                id="repo_1",
                name="Repository 1",
                url="https://repo1.example.jp/",
                updated=datetime(2026, 1, 1, 0, 0),  # noqa: DTZ001
            ),
        )
    ]

    with app.test_request_context():
        result = unwrap(cache_groups.get_task_status)()

    assert result == TaskDetail(results=expect_result, current="repo1.example.jp", total=10, done=10)
    mock_hgetall.assert_called_once_with("jcgroups_cache")
    mock_delete.assert_called_once_with("jcgroups_cache")
    mock_search.assert_called_once_with(
        RepositoriesQuery(
            q="/repo1.example.jp/",
            k="id",
            d="asc",
            p=-1,
            l=1,
        )
    )

    mocker.stopall()


def test_get_task_status_multi_try(mocker: MockerFixture, app, unwrap, repository_summaries):
    task_data = {
        b"current": b"repo2.example.jp",
        b"done": b"2",
        b"total": b"3",
        b"repo1.example.jp_0": b"{'status': 'failed', 'updated': '2026-01-01T00:00:00Z', 'code': 'timeout'}",
        b"repo1.example.jp_1": b"{'status': 'success', 'updated': '2026-01-01T00:00:00Z'}",
        b"repo2.example.jp_0": b"{'status': 'failed', 'updated': '2026-01-02T00:00:00Z', 'code': 'timeout'}",
    }
    repositories = repository_summaries(2)
    first_repo = deepcopy(repositories)
    first_repo.resources.pop(1)
    second_repo = deepcopy(repositories)
    second_repo.resources.pop(0)

    mock_hgetall = mocker.patch("server.api.cache_groups.app_cache.hgetall", return_value=task_data)
    mock_delete = mocker.patch("server.api.cache_groups.app_cache.delete")
    mock_search = mocker.patch(
        "server.api.cache_groups.search",
        side_effect=[first_repo, first_repo, second_repo],
    )

    expect_result = [
        CacheResult(
            type="cache",
            fqdn="repo1.example.jp",
            status="success",
            code=None,
            repository_cached=RepositoryCache(
                id="repo_1",
                name="Repository 1",
                url="https://repo1.example.jp/",
                updated=datetime(2026, 1, 1, 0, 0),  # noqa: DTZ001
            ),
        ),
        CacheResult(
            type="cache",
            fqdn="repo2.example.jp",
            status="failed",
            code="timeout",
            repository_cached=RepositoryCache(
                id="repo_2",
                name="Repository 2",
                url="https://repo2.example.jp/",
                updated=datetime(2026, 1, 2, 0, 0),  # noqa: DTZ001
            ),
        ),
    ]

    with app.test_request_context():
        result = unwrap(cache_groups.get_task_status)()

    assert result == TaskDetail(results=expect_result, current="repo2.example.jp", total=3, done=2)
    mock_hgetall.assert_called_once_with("jcgroups_cache")
    mock_delete.assert_not_called()
    assert mock_search.call_args_list == [
        call(
            RepositoriesQuery(
                q="/repo1.example.jp/",
                k="id",
                d="asc",
                p=-1,
                l=1,
            )
        ),
        call(
            RepositoriesQuery(
                q="/repo1.example.jp/",
                k="id",
                d="asc",
                p=-1,
                l=1,
            )
        ),
        call(
            RepositoriesQuery(
                q="/repo2.example.jp/",
                k="id",
                d="asc",
                p=-1,
                l=1,
            )
        ),
    ]

    mocker.stopall()
