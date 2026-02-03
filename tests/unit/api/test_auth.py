import typing as t

from http import HTTPStatus

from flask import session

from server.api import auth
from server.const import USER_ROLES
from server.entities.summaries import GroupSummary
from server.entities.user_detail import UserDetail
from server.services.utils.affiliations import Affiliations, _RoleGroup


if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_login_no_eppn(app, mocker: MockerFixture):
    with app.test_request_context(
        "/api/auth/login",
        headers={
            "IsMemberOf": "https://cg.gakunin.jp/gr/group1;https://cg.gakunin.jp/gr/group2",
            "DisplayName": "Test User",
        },
    ):
        resp = auth.login()
        assert resp.status_code == HTTPStatus.FOUND
        assert resp.location.endswith("/?error=401")


def test_login_not_is_member_of(app, mocker: MockerFixture):
    mock_repoadmin_user = UserDetail(
        id="test_user", user_name="Test User", eppns=["test_eppn"], groups=[GroupSummary(id="jc_test_roles_repoadm")]
    )
    mock_affiliations = Affiliations(
        roles=[_RoleGroup(repository_id="test", roles=[USER_ROLES.REPOSITORY_ADMIN])], groups=[]
    )
    with app.test_request_context(
        "/api/auth/login",
        headers={
            "eppn": "test_eppn",
            "DisplayName": "Test User",
        },
    ):
        mocker.patch("server.services.users.get_by_eppn", return_value=mock_repoadmin_user)
        mocker.patch("server.services.utils.affiliations.detect_affiliations", return_value=mock_affiliations)
        resp = auth.login()
        assert resp.status_code == HTTPStatus.FOUND
        assert resp.location.endswith("/")


def test_login_not_user_name(app, mocker: MockerFixture):
    with app.test_request_context(
        "/api/auth/login",
        headers={
            "eppn": "test_eppn",
            "IsMemberOf": "https://cg.gakunin.jp/gr/group1;https://cg.gakunin.jp/gr/group2",
        },
    ):
        mocker.patch("server.services.users.get_by_eppn", return_value=None)
        resp = auth.login()
        assert resp.status_code == HTTPStatus.FOUND
        assert resp.location.endswith("/?error=404")


def test_login_not_admin(app, mocker: MockerFixture):
    with app.test_request_context(
        "/api/auth/login",
        headers={
            "eppn": "test_eppn",
            "IsMemberOf": "https://cg.gakunin.jp/gr/group1;https://cg.gakunin.jp/gr/group2",
            "DisplayName": "Test User",
        },
    ):
        mocker.patch("server.services.permissions.extract_group_ids", return_value=["group1", "jc_test_groups_group2"])
        resp = auth.login()
        assert resp.status_code == HTTPStatus.FOUND
        assert resp.location.endswith("/?error=403")


def test_login_next(app, mocker: MockerFixture):
    mock_affiliations = Affiliations(roles=[_RoleGroup(repository_id=None, roles=[USER_ROLES.SYSTEM_ADMIN])], groups=[])
    with app.test_request_context(
        "/api/auth/login?next=users",
        headers={
            "eppn": "test_eppn",
            "IsMemberOf": "https://cg.gakunin.jp/gr/group1;https://cg.gakunin.jp/gr/jc_roles_sysadm",
            "DisplayName": "Test User",
        },
    ):
        mocker.patch("server.services.permissions.extract_group_ids", return_value=["group1", "jc_roles_sysadm"])
        mocker.patch("server.services.utils.affiliations.detect_affiliations", return_value=mock_affiliations)
        resp = auth.login()
        assert resp.status_code == HTTPStatus.FOUND
        assert resp.location.endswith("/?next=users")


def test_logout(app, mocker: MockerFixture):
    app.secret_key = "test-secret"
    with app.test_request_context("/api/auth/logout"):
        session["_id"] = "test_eppn"
        resp = auth.logout()
    assert resp.status_code == HTTPStatus.FOUND
    assert resp.location.endswith("/")
