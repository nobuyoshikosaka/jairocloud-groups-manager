import typing as t

import pytest

from flask_login import login_user

from server.const import USER_ROLES
from server.entities import map_error, map_group, map_service, map_user
from server.entities.login_user import LoginUser
from server.services.utils import permissions
from server.services.utils.affiliations import Affiliations, _Group, _RoleGroup


if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture

test_sys_admin_user = LoginUser(
    eppn="test_eppn",
    is_member_of="https://cg.gakunin.jp/gr/group1;https://cg.gakunin.jp/gr/jc_roles_sysadm_test",
    user_name="Test User",
    map_id="test_user_id",
    session_id="",
)

test_repo_admin_user = LoginUser(
    eppn="test_eppn",
    is_member_of="https://cg.gakunin.jp/gr/group1;https://cg.gakunin.jp/gr/jc_repo1_roles_repoadm_test;https://cg.gakunin.jp/gr/jc_repo2_roles_repoadm_test",
    user_name="Test User",
    map_id="test_user_id",
    session_id="",
)

mock_affiliations = Affiliations(
    roles=[
        _RoleGroup(repository_id="repo1", role=USER_ROLES.REPOSITORY_ADMIN),
        _RoleGroup(repository_id="repo2", role=USER_ROLES.REPOSITORY_ADMIN),
        _RoleGroup(repository_id="repo3", role=USER_ROLES.CONTRIBUTOR),
    ],
    groups=[
        _Group(repository_id="repo2", group_id="jc_repo2_groups_test_group2", user_defined_id="group2"),
        _Group(repository_id="repo3", group_id="jc_repo3_groups_test_group3", user_defined_id="group3"),
    ],
)

mock_affiliations_no_logged_in = Affiliations(roles=[], groups=[])

mock_extract_group_ids = [
    "jc_repo1_roles_repoadm",
    "jc_repo1_groups_test_group1",
    "jc_repo2_roles_repoadm",
    "jc_repo3_roles_contributor",
    "jc_repo4_groups_test_group2",
]


def test_extract_group_ids():
    is_member_of = ";https://cg.gakunin.jp/sp/test_sp_AAA;https://cg.gakunin.jp/gr/group1/admin;https://cg.gakunin.jp/gr/group1;https://cg.gakunin.jp/gr/group2"
    group_ids = permissions.extract_group_ids(is_member_of)
    assert group_ids == ["group1", "group2"]


def test_is_current_user_system_admin(app, mocker: MockerFixture):
    mocker.patch(
        "server.services.utils.permissions.extract_group_ids",
        return_value=["group1", "jc_roles_sysadm_test"],
    )
    with app.test_request_context("/"):
        login_user(test_sys_admin_user)
        assert permissions.is_current_user_system_admin() is True


def test_is_current_user_system_admin_not_logged_in(mocker: MockerFixture):
    mocker.patch("server.services.utils.permissions.is_user_logged_in", return_value=False)
    assert permissions.is_current_user_system_admin() is False


def test_get_permitted_repository_ids(app, mocker: MockerFixture):
    mocker.patch(
        "server.services.utils.permissions.extract_group_ids",
        return_value=["group1", "jc_roles_sysadm_test"],
    )
    mocker.patch(
        "server.services.utils.permissions.extract_group_ids",
        return_value=mock_extract_group_ids,
    )
    mocker.patch("server.services.utils.permissions.detect_affiliations", return_value=mock_affiliations)
    with app.test_request_context("/"):
        login_user(test_sys_admin_user)
        permitted_ids = permissions.get_permitted_repository_ids()
        assert permitted_ids == {"repo1", "repo2"}


def test_get_permitted_repository_ids_not_logged_in(mocker: MockerFixture):
    mocker.patch("server.services.utils.permissions.is_user_logged_in", return_value=False)
    mocker.patch(
        "server.services.utils.permissions.detect_affiliations",
        return_value=mock_affiliations_no_logged_in,
    )
    permitted_ids = permissions.get_permitted_repository_ids()
    assert permitted_ids == set()


def test_filter_permitted_group_ids(mocker: MockerFixture):
    mocker.patch("server.services.utils.permissions.get_permitted_repository_ids", return_value={"repo1", "repo2"})

    mocker.patch(
        "server.services.utils.permissions.detect_affiliations",
        return_value=mock_affiliations,
    )
    permitted_group_ids = permissions.filter_permitted_group_ids(*mock_extract_group_ids)
    assert permitted_group_ids == {"jc_repo2_groups_test_group2"}


def test_get_current_user_affiliations(app, mocker: MockerFixture):
    mocker.patch(
        "server.services.utils.permissions.extract_group_ids",
        return_value=["group1", "jc_roles_sysadm_test"],
    )
    mocker.patch("server.services.utils.permissions.detect_affiliations", return_value=mock_affiliations)
    with app.test_request_context("/"):
        login_user(test_sys_admin_user)
        affiliations = permissions.get_current_user_affiliations()
        assert affiliations == mock_affiliations


def test_get_current_user_affiliations_not_logged_in(mocker: MockerFixture):
    mocker.patch("server.services.utils.permissions.is_user_logged_in", return_value=False)
    affiliations = permissions.get_current_user_affiliations()
    assert affiliations == mock_affiliations_no_logged_in


@pytest.mark.parametrize(
    ("test_user", "expected_groups"),
    [
        (
            test_sys_admin_user,
            [
                map_service.Group(value="jc_repo2_groups_test_group2"),
                map_service.Group(value="jc_repo3_groups_test_group3"),
            ],
        ),
        (
            test_repo_admin_user,
            [
                map_service.Group(value="jc_repo2_groups_test_group2"),
            ],
        ),
    ],
)
def test_remove_info_outside_system_map_service(app, mocker: MockerFixture, test_user, expected_groups):
    entity = map_service.MapService(
        id="service1",
        groups=[
            map_service.Group(value="jc_repo2_groups_test_group2"),
            map_service.Group(value="external_group"),
            map_service.Group(value="jc_repo3_groups_test_group3"),
        ],
    )
    mocker.patch(
        "server.services.utils.permissions.detect_affiliations",
        return_value=mock_affiliations,
    )
    mocker.patch("server.services.utils.permissions.get_permitted_repository_ids", return_value={"repo1", "repo2"})
    with app.test_request_context("/"):
        login_user(test_user)
        filtered_entity = permissions.remove_info_outside_system(entity)
        assert isinstance(filtered_entity, map_service.MapService)
        if filtered_entity.groups is None:
            filtered_entity.groups = []
        assert filtered_entity.groups == expected_groups


@pytest.mark.parametrize(("test_user", "expected_member_count"), [(test_sys_admin_user, 2), (test_repo_admin_user, 1)])
def test_remove_info_outside_system_map_group(app, mocker: MockerFixture, test_user, expected_member_count):
    entity = map_group.MapGroup(
        id="jc_repo1_groups_test_group1",
        members=[
            map_group.MemberGroup(value="jc_repo2_groups_test_group2"),
            map_group.MemberGroup(value="jc_repo3_groups_test_group3"),
            map_group.MemberGroup(value="external_group"),
        ],
    )
    mocker.patch(
        "server.services.utils.permissions.detect_affiliations",
        return_value=mock_affiliations,
    )
    mocker.patch("server.services.utils.permissions.get_permitted_repository_ids", return_value={"repo1", "repo2"})
    with app.test_request_context("/"):
        login_user(test_user)
        filtered_entity = permissions.remove_info_outside_system(entity)
        assert isinstance(filtered_entity, map_group.MapGroup)
        if filtered_entity.members is None:
            filtered_entity.members = []
        assert len(filtered_entity.members) == expected_member_count


@pytest.mark.parametrize(("test_user", "expected_group_count"), [(test_sys_admin_user, 2), (test_repo_admin_user, 1)])
def test_remove_info_outside_system_map_user(app, mocker: MockerFixture, test_user, expected_group_count):
    entity = map_user.MapUser(
        id="user1",
        groups=[
            map_user.Group(value="jc_repo2_groups_test_group2"),
            map_user.Group(value="external_group"),
            map_user.Group(value="jc_repo3_groups_test_group3"),
        ],
    )
    mocker.patch(
        "server.services.utils.permissions.detect_affiliations",
        return_value=mock_affiliations,
    )
    mocker.patch("server.services.utils.permissions.get_permitted_repository_ids", return_value={"repo1", "repo2"})
    with app.test_request_context("/"):
        login_user(test_user)
        filtered_entity = permissions.remove_info_outside_system(entity)
        assert isinstance(filtered_entity, map_user.MapUser)
        if filtered_entity.groups is None:
            filtered_entity.groups = []
        assert len(filtered_entity.groups) == expected_group_count


def test_remove_info_outside_system_other_entity():
    entity = map_error.MapError(status="404", scim_type="noTarget", detail="Not found")
    filtered_entity = permissions.remove_info_outside_system(entity)
    assert filtered_entity == entity
