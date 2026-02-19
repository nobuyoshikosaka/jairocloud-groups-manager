import inspect
import typing as t

import pytest

from flask import Flask
from pytest_mock import MockerFixture

from server.api import groups as groups_api
from server.api.groups import (
    DeleteGroupsRequest,
    GroupDetail,
    GroupPatchRequest,
    GroupsQuery,
    ResourceInvalid,
    ResourceNotFound,
)
from server.api.schemas import (
    GroupPatchOperation,
)
from server.entities.group_detail import Repository
from server.entities.search_request import SearchResult
from tests.helpers import UnexpectedError


if t.TYPE_CHECKING:
    from flask import Flask
    from pytest_mock import MockerFixture

    from server.config import RuntimeConfig


def test_get_success(app: Flask, mocker: MockerFixture) -> None:
    """Tests group search with query returns 200 and results."""

    expected_group = SearchResult(
        resources=[],
        total=0,
        page_size=0,
        offset=0,
    )
    query = GroupsQuery(
        q="test-group", r=["repo1", "repo2"], u=["user1"], s=0, v=1, k="display_name", d="asc", p=1, l=30
    )
    expected_status = 200
    mocker.patch("server.api.groups.has_permission", return_value=True)
    search_mock = mocker.patch("server.services.groups.search", return_value=expected_group)

    original_func = inspect.unwrap(groups_api.get)
    result, status = original_func(query)

    assert result == expected_group
    assert status == expected_status
    assert search_mock.call_args[0][0] == query


def test_post_success(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests group creation returns group info, 201, and Location header."""
    expected_group = GroupDetail(
        id=gen_group_id("g1"),
        display_name="test",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r1", service_name="repo1"),
    )
    expected_status = 201
    url_for_patch = f"https://host/api/groups/{expected_group.id}"
    expected_headers = {"Location": url_for_patch}

    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.create", return_value=expected_group)
    mocker.patch("server.api.groups.url_for", return_value=url_for_patch)

    original_func = inspect.unwrap(groups_api.post)
    result, status, headers = original_func(expected_group)

    assert result == expected_group
    assert status == expected_status
    assert headers == expected_headers


def test_post_failure_returns_error_response_and_400(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests group creation failure returns ErrorResponse and 400."""

    expected_group = GroupDetail(
        id=gen_group_id("g1"),
        display_name="test",
        public=True,
        member_list_visibility="Private",
        repository=None,
    )
    error_detail = "repository id is required"
    expected_status = 400
    mocker.patch("server.api.groups.has_permission", return_value=True)

    original_func = inspect.unwrap(groups_api.post)
    result, status = original_func(expected_group)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status
    assert result.message == error_detail


def test_post_already_exists_returns_error_response_and_409(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests group creation with existing group ID returns ErrorResponse and 409."""

    group = GroupDetail(
        id=gen_group_id("g1"),
        display_name="test",
        public=True,
        member_list_visibility="Hidden",
        repository=Repository(id="r1", service_name="repo1"),
    )
    error_detail = "id already exist"
    expected_status = 409

    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.create", side_effect=ResourceInvalid(error_detail))
    mocker.patch("server.api.groups.url_for", return_value=f"https://host/api/groups/{group.id}")

    original_func = inspect.unwrap(groups_api.post)
    result, status = original_func(group)
    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status
    assert result.message == error_detail


def test_post_unexpected_error_returns_exception(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests group creation with not-registered group ID and unexpected error returns the error as-is."""
    group = GroupDetail(
        id=gen_group_id("g1"),
        display_name="test",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r1", service_name="repo1"),
    )
    error_detail = "unexpected error occurred"

    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.create", side_effect=UnexpectedError(error_detail))
    mocker.patch("server.api.groups.url_for", return_value=f"https://host/api/groups/{group.id}")

    original_func = inspect.unwrap(groups_api.post)

    with pytest.raises(UnexpectedError) as exc_info:
        original_func(group)
    assert str(exc_info.value) == error_detail


def test_id_get_success_admin(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_get returns group info and 200 when group exists and user is admin."""
    group_id = gen_group_id("g1")
    expected_group = GroupDetail(
        id=group_id,
        display_name="test-group",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r1", service_name="repo1"),
    )
    expected_status = 200

    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.get_by_id", return_value=expected_group)

    original_func = inspect.unwrap(groups_api.id_get)
    result, status = original_func(group_id)
    assert result == expected_group
    assert status == expected_status


def test_id_get_success_group_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_get returns group info and 200 when user has permission for the group."""
    group_id = gen_group_id("g2")
    expected_group = GroupDetail(
        id=group_id,
        display_name="test-group2",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r2", service_name="repo2"),
    )
    expected_status = 200

    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.get_by_id", return_value=expected_group)

    original_func = inspect.unwrap(groups_api.id_get)
    result, status = original_func(group_id)

    assert result == expected_group
    assert status == expected_status


def test_id_get_forbidden_no_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_get returns ErrorResponse and 403 when user lacks permission for the group."""
    group_id = gen_group_id("g3")
    group = GroupDetail(
        id=group_id,
        display_name="test-group3",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r3", service_name="repo3"),
    )
    expected_status = 403

    mocker.patch("server.api.groups.has_permission", return_value=False)
    mocker.patch("server.services.groups.get_by_id", return_value=group)

    original_func = inspect.unwrap(groups_api.id_get)
    result, status = original_func(group_id)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status


def test_id_get_not_found(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_get returns ErrorResponse and 404 when group does not exist."""
    group_id = gen_group_id("g4")
    expected_status = 404
    not_found_message = f"'{group_id}' Not Found"

    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.get_by_id", return_value=None)

    original_func = inspect.unwrap(groups_api.id_get)
    result, status = original_func(group_id)
    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status
    assert not_found_message in result.message


def test_id_get_unexpected_error(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_get returns the unexpected error as-is when an unexpected error occurs during group search."""
    group_id = gen_group_id("g5")
    error_detail = "unexpected error in id_get"

    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.get_by_id", side_effect=UnexpectedError(error_detail))

    original_func = inspect.unwrap(groups_api.id_get)
    with pytest.raises(UnexpectedError) as exc_info:
        original_func(group_id)
    assert str(exc_info.value) == error_detail


def test_id_put_success_admin(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_put returns updated group info and 200 for system admin."""
    group_id = gen_group_id("g1")
    expected_group = GroupDetail(
        id=group_id,
        display_name="updated-group",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r1", service_name="repo1"),
    )
    expected_status = 200

    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.update", return_value=expected_group)

    original_func = inspect.unwrap(groups_api.id_put)
    result, status = original_func(group_id, expected_group)

    assert result == expected_group
    assert status == expected_status


def test_id_put_success_group_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_put returns updated group info and 200 for user with permission."""
    group_id = gen_group_id("g2")
    expected_group = GroupDetail(
        id=group_id,
        display_name="updated-group2",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r2", service_name="repo2"),
    )
    expected_status = 200
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.update", return_value=expected_group)

    original_func = inspect.unwrap(groups_api.id_put)
    result, status = original_func(group_id, expected_group)

    assert result == expected_group
    assert status == expected_status


def test_id_put_forbidden_no_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_put returns ErrorResponse and 403 when user lacks permission for the group."""
    group_id = gen_group_id("g3")
    group = GroupDetail(
        id=group_id,
        display_name="test-group3",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r3", service_name="repo3"),
    )
    expected_status = 403
    expected_message = f"Not have permission to edit {group_id}."
    mocker.patch("server.api.groups.has_permission", return_value=False)
    mocker.patch("server.services.groups.update", return_value=group)

    original_func = inspect.unwrap(groups_api.id_put)
    result, status = original_func(group_id, group)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status
    assert expected_message in result.message


def test_id_put_update_error_returns_409(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_put returns ErrorResponse and 409 when update error occurs."""
    group_id = gen_group_id("g4")
    group = GroupDetail(
        id=group_id,
        display_name="test-group4",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r4", service_name="repo4"),
    )
    error_detail = "update error"
    expected_status = 409
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.update", side_effect=ResourceInvalid(error_detail))

    original_func = inspect.unwrap(groups_api.id_put)
    result, status = original_func(group_id, group)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status
    assert error_detail in result.message


def test_id_put_not_found_returns_404(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_put returns ErrorResponse and 404 when group not found."""
    group_id = gen_group_id("g5")
    group = GroupDetail(
        id=group_id,
        display_name="test-group5",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r5", service_name="repo5"),
    )
    error_detail = "not found"
    expected_status = 404
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.update", side_effect=ResourceNotFound(error_detail))

    original_func = inspect.unwrap(groups_api.id_put)
    result, status = original_func(group_id, group)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status
    assert error_detail in result.message


def test_id_put_unexpected_error(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_put returns the unexpected error as-is when an unexpected error occurs during group update."""
    group_id = gen_group_id("g6")
    group = GroupDetail(
        id=group_id,
        display_name="test-group6",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r6", service_name="repo6"),
    )
    error_detail = "unexpected error in id_put"
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.update", side_effect=UnexpectedError(error_detail))

    original_func = inspect.unwrap(groups_api.id_put)
    with pytest.raises(UnexpectedError) as exc_info:
        original_func(group_id, group)

    assert str(exc_info.value) == error_detail


def test_id_patch_success_admin(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_patch returns updated group info and 200 for system admin."""
    group_id = gen_group_id("g1")
    expected_group = GroupDetail(
        id=group_id,
        display_name="patched-group",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r1", service_name="repo1"),
    )
    patch_body = GroupPatchRequest(operations=[GroupPatchOperation(op="add", path="member", value=["user1"])])
    expected_status = 200
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.update_member", return_value=expected_group)

    original_func = inspect.unwrap(groups_api.id_patch)
    result, status = original_func(group_id, patch_body)

    assert result == expected_group
    assert status == expected_status


def test_id_patch_success_group_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_patch returns updated group info and 200 for user with permission."""
    group_id = gen_group_id("g2")
    expected_group = GroupDetail(
        id=group_id,
        display_name="patched-group2",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r2", service_name="repo2"),
    )
    patch_body = GroupPatchRequest(operations=[GroupPatchOperation(op="remove", path="member", value=["user1"])])
    expected_status = 200
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.update_member", return_value=expected_group)

    original_func = inspect.unwrap(groups_api.id_patch)
    result, status = original_func(group_id, patch_body)

    assert result == expected_group
    assert status == expected_status


def test_id_patch_forbidden_no_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_patch returns ErrorResponse and 403 when user lacks permission for the group."""
    group_id = gen_group_id("g3")
    group = GroupDetail(
        id=group_id,
        display_name="test-group3",
        public=True,
        member_list_visibility="Public",
        repository=Repository(id="r3", service_name="repo3"),
    )
    patch_body = GroupPatchRequest(operations=[GroupPatchOperation(op="add", path="member", value=["user1"])])
    expected_status = 403
    mocker.patch("server.api.groups.has_permission", return_value=False)
    mocker_update_member = mocker.patch("server.services.groups.update_member", return_value=group)

    original_func = inspect.unwrap(groups_api.id_patch)
    result, status = original_func(group_id, patch_body)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status
    assert mocker_update_member.return_value == group


def test_id_patch_update_error_returns_409(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_patch returns ErrorResponse and 409 when update error occurs."""
    group_id = gen_group_id("g4")
    patch_body = GroupPatchRequest(operations=[GroupPatchOperation(op="add", path="member", value=["user1"])])
    error_detail = "patch error"
    expected_status = 409

    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.update_member", side_effect=ResourceInvalid(error_detail))

    original_func = inspect.unwrap(groups_api.id_patch)
    result, status = original_func(group_id, patch_body)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status
    assert error_detail in result.message


def test_id_patch_not_found_returns_404(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_patch returns ErrorResponse and 404 when group not found."""
    group_id = gen_group_id("g5")
    patch_body = GroupPatchRequest(operations=[GroupPatchOperation(op="add", path="member", value=["user1"])])
    error_detail = "not found"
    expected_status = 404

    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.update_member", side_effect=ResourceNotFound(error_detail))

    original_func = inspect.unwrap(groups_api.id_patch)
    result, status = original_func(group_id, patch_body)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status
    assert error_detail in result.message


def test_id_patch_unexpected_error(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_patch returns the unexpected error as-is when an unexpected error occurs during group patch."""
    group_id = gen_group_id("g6")
    patch_body = GroupPatchRequest(operations=[GroupPatchOperation(op="add", path="member", value=["user1"])])
    error_detail = "unexpected error in id_patch"

    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.update_member", side_effect=UnexpectedError(error_detail))

    original_func = inspect.unwrap(groups_api.id_patch)
    with pytest.raises(UnexpectedError) as exc_info:
        original_func(group_id, patch_body)
    assert str(exc_info.value) == error_detail


def test_id_delete_success_admin(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_delete returns None and 204 for system admin."""
    group_id: str = gen_group_id("g1")
    expected_status: int = 204
    mocker.patch("server.api.groups.has_permission", return_value=True)
    delete_mock = mocker.patch("server.services.groups.delete_by_id", return_value=None)
    original_func = inspect.unwrap(groups_api.id_delete)
    result, status = original_func(group_id)
    assert not result
    assert status == expected_status
    delete_mock.assert_called_once_with(group_id)


def test_id_delete_success_group_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_delete returns None and 204 for user with permission."""
    group_id: str = gen_group_id("g2")
    expected_status: int = 204
    mocker.patch("server.api.groups.has_permission", return_value=True)
    delete_mock = mocker.patch("server.services.groups.delete_by_id", return_value=None)
    original_func = inspect.unwrap(groups_api.id_delete)
    result, status = original_func(group_id)
    assert not result
    assert status == expected_status
    delete_mock.assert_called_once_with(group_id)


def test_id_delete_forbidden_no_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_delete returns ErrorResponse and 403 when user lacks permission for the group."""
    group_id: str = gen_group_id("g3")
    expected_status: int = 403
    mocker.patch("server.api.groups.has_permission", return_value=False)
    original_func = inspect.unwrap(groups_api.id_delete)
    result, status = original_func(group_id)
    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status


def test_id_delete_unexpected_error(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests id_delete returns the unexpected error as-is when an unexpected error occurs during group deletion."""
    group_id: str = gen_group_id("g4")
    error_detail: str = "unexpected error in id_delete"
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.delete_by_id", side_effect=UnexpectedError(error_detail))
    original_func = inspect.unwrap(groups_api.id_delete)
    with pytest.raises(UnexpectedError) as exc_info:
        original_func(group_id)
    assert str(exc_info.value) == error_detail


def test_delete_post_success_admin(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests delete_post returns None and 204 for system admin (all groups deleted)."""
    group_ids = {gen_group_id("g1"), gen_group_id("g2")}
    body = DeleteGroupsRequest(group_ids=group_ids)
    expected_status = 204
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.delete_multiple", return_value=None)

    original_func = inspect.unwrap(groups_api.delete_post)
    result, status = original_func(body)

    assert not result
    assert status == expected_status


def test_delete_post_partial_failure_admin(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests delete_post returns ErrorResponse and 500 for system admin (partial failure)."""
    group_ids = {gen_group_id("g1"), gen_group_id("g2")}
    body = DeleteGroupsRequest(group_ids=group_ids)
    failed_group = gen_group_id("g2")
    error_message = f"{failed_group} is failed"
    expected_status = 500
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch(
        "server.services.groups.delete_multiple", return_value=groups_api.ErrorResponse(code="", message=error_message)
    )

    original_func = inspect.unwrap(groups_api.delete_post)
    result, status = original_func(body)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status


def test_delete_post_all_failure_admin(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests delete_post returns ErrorResponse and 500 for system admin (all failure)."""
    group_ids = {gen_group_id("g3"), gen_group_id("g4")}
    body = DeleteGroupsRequest(group_ids=group_ids)
    failed_group = gen_group_id("g3")
    error_message = f"{failed_group} is failed"
    expected_status = 500
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch(
        "server.services.groups.delete_multiple", return_value=groups_api.ErrorResponse(code="", message=error_message)
    )

    original_func = inspect.unwrap(groups_api.delete_post)
    result, status = original_func(body)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status


def test_delete_post_success_group_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests delete_post returns None and 204 for user with permission (all groups deleted)."""
    group_ids = {gen_group_id("g5"), gen_group_id("g6")}
    body = DeleteGroupsRequest(group_ids=group_ids)
    expected_status = 204
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.delete_multiple", return_value=None)

    original_func = inspect.unwrap(groups_api.delete_post)
    result, status = original_func(body)

    assert not result
    assert status == expected_status


def test_delete_post_partial_failure_group_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests delete_post returns ErrorResponse and 500 for user with permission (partial failure)."""
    group_ids = {gen_group_id("g7"), gen_group_id("g8")}
    body = DeleteGroupsRequest(group_ids=group_ids)

    failed_group = gen_group_id("g8")
    error_message = f"{failed_group} is failed"
    expected_status = 500
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch(
        "server.services.groups.delete_multiple", return_value=groups_api.ErrorResponse(code="", message=error_message)
    )

    original_func = inspect.unwrap(groups_api.delete_post)
    result, status = original_func(body)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status


def test_delete_post_all_failure_group_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests delete_post returns ErrorResponse and 500 for user with permission (all failure)."""
    group_ids = {gen_group_id("g9"), gen_group_id("g10")}
    body = DeleteGroupsRequest(group_ids=group_ids)

    failed_group = gen_group_id("g9")
    error_message = f"{failed_group} is failed"
    expected_status = 500
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch(
        "server.services.groups.delete_multiple", return_value=groups_api.ErrorResponse(code="", message=error_message)
    )

    original_func = inspect.unwrap(groups_api.delete_post)
    result, status = original_func(body)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status


def test_delete_post_partial_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests delete_post returns ErrorResponse and 403 for user with partial permission"""
    group_id1: str = gen_group_id("g11")
    group_id2: str = gen_group_id("g12")
    group_ids: set[str] = {group_id1, group_id2}
    body: DeleteGroupsRequest = DeleteGroupsRequest(group_ids=group_ids)
    expected_status: int = 403
    mocker.patch("server.services.utils.filter_permitted_group_ids", return_value=[group_id1])
    mocker.patch("server.api.groups.is_current_user_system_admin", return_value=False)
    with app.app_context(), app.test_request_context():
        original_func = inspect.unwrap(groups_api.delete_post)
        result, status = original_func(body)
    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status


def test_delete_post_no_permission(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests delete_post returns ErrorResponse and 403 for user with no permission."""
    group_ids = {gen_group_id("g13"), gen_group_id("g14")}
    body = DeleteGroupsRequest(group_ids=group_ids)

    expected_status = 403
    mocker.patch("server.api.groups.has_permission", return_value=False)
    mocker.patch("server.services.groups.delete_multiple", return_value=None)

    original_func = inspect.unwrap(groups_api.delete_post)
    result, status = original_func(body)

    assert isinstance(result, groups_api.ErrorResponse)
    assert status == expected_status


def test_delete_post_unexpected_error(app: Flask, gen_group_id, mocker: MockerFixture) -> None:
    """Tests delete_post returns the unexpected error as-is when an unexpected error occurs during delete_post."""
    group_ids = {gen_group_id("g15"), gen_group_id("g16")}
    body = DeleteGroupsRequest(group_ids=group_ids)

    error_detail = "unexpected error in delete_post"
    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.groups.delete_multiple", side_effect=UnexpectedError(error_detail))

    original_func = inspect.unwrap(groups_api.delete_post)
    with pytest.raises(UnexpectedError) as exc_info:
        original_func(body)

    assert str(exc_info.value) == error_detail


def test_filter_options(app: Flask, mocker: MockerFixture) -> None:
    """Tests filter_options endpoint executes successfully."""
    search_result: SearchResult = SearchResult(resources=[], total=0, page_size=0, offset=0)

    mocker.patch("server.api.groups.has_permission", return_value=True)
    mocker.patch("server.services.filter_options.search_groups_options", return_value=[])
    mocker.patch("server.services.token.get_access_token", return_value="dummy_token")
    mocker.patch("server.services.repositories.search", return_value=search_result)

    original_func = inspect.unwrap(groups_api.filter_options)
    result = original_func()

    assert isinstance(result, list)


@pytest.fixture
def gen_group_id(test_config: RuntimeConfig) -> t.Callable[[str], str]:

    def _gen_group_id(user_defined_id: str) -> str:
        pattern = test_config.GROUPS.id_patterns.user_defined
        return pattern.format(repository_id="repo_id", user_defined_id=user_defined_id)

    return _gen_group_id
