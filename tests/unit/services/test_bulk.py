import typing as t

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid7

import pytest

from server.db.history import Files, _FileContent
from server.entities.bulk import (
    CheckResult,
    HistorySummary,
    RepositoryMember,
    ResultSummary,
    UserAggregated,
    ValidateSummary,
)
from server.entities.bulk_request import BulkOperation, BulkResponse
from server.entities.map_error import MapError
from server.entities.map_group import MapGroup, MemberGroup, MemberUser
from server.entities.map_user import EPPN, Email, Group, MapUser
from server.entities.patch_request import AddOperation, RemoveOperation
from server.entities.search_request import SearchResponse
from server.entities.summaries import GroupSummary
from server.entities.user_detail import UserDetail
from server.exc import OAuthTokenError, RecordNotFound, ResourceInvalid, ResourceNotFound
from server.services import bulks
from server.services.utils.affiliations import Affiliations, _Group


if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture


def assert_unordered_model_list_equal(list1, list2):
    def to_tuple(x):
        def deep_tuple(obj):
            if isinstance(obj, dict):
                return tuple(sorted((k, deep_tuple(v)) for k, v in obj.items()))
            if isinstance(obj, list):
                return tuple(deep_tuple(i) for i in obj)
            return obj

        return deep_tuple(x.dict())

    assert set(map(to_tuple, list1)) == set(map(to_tuple, list2))


def test_validate_upload_data(app, mocker: MockerFixture):
    operator_id = "test_user_id"
    operator_name = "test_user_name"
    temp_file_id = uuid7()
    file_path = "/var/tmp/test_file.csv"  # noqa: S108
    file_content = _FileContent(
        repositories=[{"id": "repo1", "serviceName": "test_service"}],
        groups=[{"id": "group1", "displayName": "Group 1"}, {"id": "group2", "displayName": "Group 2"}],
        users=[{"id": "user1", "userName": "User 1"}, {"id": "user2", "userName": "User 2"}],
    )
    files = Files()
    files.id = temp_file_id
    files.file_path = file_path
    files.file_content = file_content
    mock_get_file_by_id = mocker.patch("server.services.history_table.get_file_by_id", return_value=files)
    repository_member = RepositoryMember(groups={"group1", "group2"}, users={"user1", "user2"})
    mock_get_repository_member = mocker.patch(
        "server.services.bulks.get_repository_member", return_value=repository_member
    )
    mocker.patch("server.services.bulks.build_user_from_file", return_value=(None, None))
    mocker.patch("server.services.bulks.build_user_detail_from_dict", return_value=mocker.MagicMock())
    mocker.patch("server.services.bulks.build_user_detail_from_dict_by_name", return_value=mocker.MagicMock())
    missing_users = [UserDetail(id="user3", user_name="User 3")]
    mocker.patch("server.services.bulks._get_missing_users", return_value=missing_users)
    mocker.patch("server.services.bulks._get_repo_user_by_id", return_value=None)
    check_results = [
        CheckResult(
            id="user1",
            eppn=["eppn1"],
            email=["user1@example.com"],
            user_name="User 1",
            groups={"group1"},
            status="update",
            code=None,
        ),
        CheckResult(
            id="user2",
            eppn=["eppn2"],
            email=["user2@example.com"],
            user_name="User 2",
            groups={"group2"},
            status="skip",
            code=None,
        ),
        CheckResult(
            id="user3",
            eppn=["eppn3"],
            email=["user3@example.com"],
            user_name="User 3",
            groups={"group1", "group2"},
            status="create",
            code=None,
        ),
    ]
    summary = HistorySummary(create=1, update=1, delete=0, skip=1, error=0)
    mocker.patch(
        "server.services.bulks._build_check_results",
        return_value=(
            check_results,
            summary,
        ),
    )
    mock_create_upload = mocker.patch(
        "server.services.history_table.create_upload",
        return_value=uuid7(),
    )
    validate_summary = ValidateSummary(
        results=check_results, summary=summary, missing_user=missing_users, offset=0, page_size=3
    )
    result = bulks.validate_upload_data(operator_id, operator_name, temp_file_id)
    assert isinstance(result, UUID)
    mock_get_file_by_id.assert_called_once_with(temp_file_id)
    mock_get_repository_member.assert_called_once_with("repo1")
    mock_create_upload.assert_called_once_with(
        operator_id=operator_id,
        operator_name=operator_name,
        file_id=temp_file_id,
        results=validate_summary.model_dump(mode="json"),
    )


def test_get_repository_member(app, mocker: MockerFixture):
    repository_id = "repo1"
    groups = {"group1", "group2"}
    users = {"user1", "user2"}
    mock_search = mocker.patch(
        "server.services.groups.search",
        return_value=SearchResponse[MapGroup](
            total_results=2,
            start_index=1,
            items_per_page=20,
            resources=[
                MapGroup(id="group1", display_name="Group 1", members=[MemberUser(value="user1", display="User 1")]),
                MapGroup(
                    id="group2",
                    display_name="Group 2",
                    members=[
                        MemberUser(value="user2", display="User 2"),
                        MemberGroup(value="group1", display="Group 1"),
                    ],
                ),
            ],
        ),
    )
    expected = RepositoryMember(groups=groups, users=users)
    result = bulks.get_repository_member(repository_id)
    mock_search.assert_called_once()
    assert result == expected


def test_build_user_from_file(app, mocker: MockerFixture):
    header = [
        "id",
        "user_name",
        "groups[].id",
        "groups[].name",
        "edu_person_principal_names[]",
        "emails[]",
        "preferred_language",
    ]
    meta = ["readonly", "readonly", "writable", "readonly", "readonly", "readonly", "readonly"]
    data1 = ["user1", "User 1", "jc_repo1_gr_test_group1", "Group 1", "test@eppn", "user1@example.com", "en"]
    data2 = ["user1", "User 1", "jc_repo1_gr_test_group2", "Group 2", "test@eppn", "user1@example.com", "en"]
    data3 = ["", "User 2", "jc_repo1_gr_test_group1", "Group 1", "test@eppn", "user2@example.com", "ja"]
    data4 = ["", "User 3", "jc_repo1_gr_test_group1", "Group 1", "test@eppn", "user2@example.com", "ja"]
    data5 = []
    data6 = ["", "", "jc_repo1_gr_test_group1", "Group 1", "test@eppn", "user2@example.com", "ja"]
    rows = [iter([header, meta, data1, data2, data3, data4, data5, data6])]
    mock_read_file = mocker.patch("server.services.bulks._read_file", return_value=iter(rows))
    expected_data = {
        "user1": {
            "user_name": ["User 1", "User 1"],
            "groups[].id": ["jc_repo1_gr_test_group1", "jc_repo1_gr_test_group2"],
            "groups[].name": ["Group 1", "Group 2"],
            "edu_person_principal_names[]": ["test@eppn", "test@eppn"],
            "emails[]": ["user1@example.com", "user1@example.com"],
            "preferred_language": ["en", "en"],
        }
    }
    expected_new_data = {
        "User 2": {
            "id": [""],
            "groups[].id": ["jc_repo1_gr_test_group1"],
            "groups[].name": ["Group 1"],
            "edu_person_principal_names[]": ["test@eppn"],
            "emails[]": ["user2@example.com"],
            "preferred_language": ["ja"],
        },
        "User 3": {
            "id": [""],
            "groups[].id": ["jc_repo1_gr_test_group1"],
            "groups[].name": ["Group 1"],
            "edu_person_principal_names[]": ["test@eppn"],
            "emails[]": ["user2@example.com"],
            "preferred_language": ["ja"],
        },
    }
    dummy_file_path = "/var/tmp/test_file.csv"  # noqa: S108
    data, new_data = bulks.build_user_from_file(dummy_file_path)
    mock_read_file.assert_called_once_with(dummy_file_path)
    assert data == expected_data
    assert new_data == expected_new_data


def test_build_user_from_file_with_exception(app, mocker: MockerFixture):
    dummy_file_path = "/var/tmp/test_file.css"  # noqa: S108
    expected_error_message = f"{Path(dummy_file_path).suffix}: Unsupported file format."
    mock_read_file = mocker.patch(
        "server.services.bulks._read_file",
        side_effect=ResourceInvalid(expected_error_message),
    )
    with pytest.raises(ResourceNotFound) as exc:
        bulks.build_user_from_file(dummy_file_path)
    mock_read_file.assert_called_once_with(dummy_file_path)
    assert str(exc.value) == expected_error_message


@pytest.mark.parametrize(
    ("file_path", "expected"),
    [
        ("/var/tmp/test_file.csv", [["id", "name"], ["1", "A"]]),  # noqa: S108
        ("/var/tmp/test_file.xlsx", [[1, "A"], [2, "B"]]),  # noqa: S108
    ],
)
def test__read_file(app, mocker: MockerFixture, file_path, expected):
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("pathlib.Path.open", mocker.mock_open(read_data="dummy"))
    mocker.patch("csv.reader", return_value=iter(expected))
    mock_ws = mocker.MagicMock()
    mock_ws.iter_rows.return_value = iter(expected)
    mock_wb = mocker.MagicMock()
    mock_wb.active = mock_ws
    mocker.patch("openpyxl.load_workbook", return_value=mock_wb)
    result = bulks._read_file(file_path)  # noqa: SLF001
    assert list(next(result)) == expected


def test__read_file_not_ws(app, mocker: MockerFixture):
    file_path = "/var/tmp/test_file.xlsx"  # noqa: S108
    expected = [["id", "name"], ["1", "A"]]

    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("pathlib.Path.open", mocker.mock_open(read_data="dummy"))
    mock_ws = mocker.MagicMock()
    mock_ws.iter_rows.return_value = iter(expected)
    mock_wb = mocker.MagicMock()
    mock_wb.active = None
    mocker.patch("openpyxl.load_workbook", return_value=mock_wb)
    with pytest.raises(ResourceInvalid) as exc:  # noqa: PT012
        result = bulks._read_file(file_path)  # noqa: SLF001
        next(result)
    assert str(exc.value) == f"{file_path}: No active sheet found in the Excel file."


@pytest.mark.parametrize(
    ("file_path", "file_exist", "expected", "expected_exception"),
    [
        ("/var/tmp/test_file.csv", False, "/var/tmp/test_file.csv: File not found.", ResourceNotFound),  # noqa: S108
        ("/var/tmp/test_file.css", True, ".css: Unsupported file format.", ResourceInvalid),  # noqa: S108
    ],
)
def test__read_file_with_exception(app, mocker: MockerFixture, file_path, file_exist, expected, expected_exception):
    mocker.patch("pathlib.Path.exists", return_value=file_exist)
    with pytest.raises(expected_exception) as exc:  # noqa: PT012
        result = bulks._read_file(file_path)  # noqa: SLF001
        next(result)
    assert str(exc.value) == expected


def test_build_user_detail_from_dict(app, mocker: MockerFixture):
    data = {
        "user1": {
            "user_name": ["User 1", "User 1"],
            "groups[].id": ["jc_repo1_gr_test_group1", "jc_repo1_gr_test_group2", "jc_repo1_gr_test_group3"],
            "groups[].name": ["Group 1", "Group 2"],
            "edu_person_principal_names[]": ["test@eppn", "test@eppn"],
            "emails[]": ["user1@example.com", "user1@example.com"],
            "preferred_language": ["en", "en"],
        },
        "user2": {
            "user_name": ["User 2", "User 2"],
            "groups[].id": ["jc_repo1_gr_test_group1"],
            "groups[].name": ["Group 1", "Group 2"],
            "edu_person_principal_names[]": ["test@eppn", "test@eppn"],
            "emails[]": ["user2@example.com", "user2@example.com"],
            "preferred_language": ["ja", "ja"],
        },
        "": {
            "user_name": [""],
            "groups[].id": [""],
            "groups[].name": [""],
            "edu_person_principal_names[]": [""],
            "emails[]": [""],
            "preferred_language": [""],
        },
    }
    expected = UserAggregated(
        root=[
            UserDetail(
                id="user1",
                user_name="User 1",
                groups=[
                    GroupSummary(id="jc_repo1_gr_test_group1", display_name="Group 1"),
                    GroupSummary(id="jc_repo1_gr_test_group2", display_name="Group 2"),
                    GroupSummary(id="jc_repo1_gr_test_group3"),
                ],
                eppns=["test@eppn"],
                emails=["user1@example.com"],
                preferred_language="en",
            ),
            UserDetail(
                id="user2",
                user_name="User 2",
                groups=[
                    GroupSummary(id="jc_repo1_gr_test_group1", display_name="Group 1"),
                ],
                eppns=["test@eppn"],
                emails=["user2@example.com"],
                preferred_language="ja",
            ),
        ]
    )
    assert bulks.build_user_detail_from_dict(data) == expected


def test_build_user_detail_from_dict_by_name(app, mocker: MockerFixture):
    data = {
        "User 2": {
            "id": [""],
            "groups[].id": ["jc_repo1_gr_test_group1"],
            "groups[].name": ["Group 1"],
            "edu_person_principal_names[]": ["test@eppn"],
            "emails[]": ["user2@example.com"],
            "preferred_language": ["ja"],
        },
        "User 3": {
            "id": [""],
            "groups[].id": ["jc_repo1_gr_test_group1"],
            "groups[].name": ["Group 1", ""],
            "edu_person_principal_names[]": ["test@eppn"],
            "emails[]": ["user3@example.com"],
            "preferred_language": ["ja"],
        },
        "": {
            "id": [""],
            "groups[].id": [""],
            "groups[].name": [""],
            "edu_person_principal_names[]": [""],
            "emails[]": [""],
            "preferred_language": [""],
        },
    }
    expected = UserAggregated(
        root=[
            UserDetail(
                user_name="User 2",
                groups=[
                    GroupSummary(id="jc_repo1_gr_test_group1", display_name="Group 1"),
                ],
                eppns=["test@eppn"],
                emails=["user2@example.com"],
                preferred_language="ja",
            ),
            UserDetail(
                user_name="User 3",
                groups=[
                    GroupSummary(id="jc_repo1_gr_test_group1", display_name="Group 1"),
                ],
                preferred_language="ja",
                eppns=["test@eppn"],
                emails=["user3@example.com"],
            ),
        ]
    )
    assert bulks.build_user_detail_from_dict_by_name(data) == expected


@pytest.mark.parametrize(
    ("repository_member", "file_users_id", "expected"),
    [
        (RepositoryMember(groups={"group1", "group2"}, users={"user1", "user2"}), {"user1", "user2"}, []),
        (
            RepositoryMember(groups={"group1", "group2"}, users={"user1", "user2"}),
            {"user2"},
            [UserDetail(id="user1", user_name="User 1", eppns=["test@eppn"], emails=["user1@example.com"])],
        ),
    ],
)
def test__get_missing_users(app, mocker: MockerFixture, repository_member, file_users_id, expected):
    mocker.patch(
        "server.services.users.search",
        return_value=SearchResponse[MapUser](
            total_results=1,
            start_index=0,
            items_per_page=20,
            resources=[
                MapUser(
                    id="user1",
                    user_name="User 1",
                    edu_person_principal_names=[EPPN(value="test@eppn")],
                    emails=[Email(value="user1@example.com")],
                )
            ],
        ),
    )
    result = bulks._get_missing_users(repository_member, file_users_id)  # noqa: SLF001
    assert result == expected


@pytest.mark.parametrize(
    ("repository_member", "file_users_id", "expected"),
    [
        (RepositoryMember(groups={"group1", "group2"}, users={"user1", "user2"}), {"user3"}, dict[str, UserDetail]()),
        (
            RepositoryMember(groups={"group1", "group2"}, users={"user1", "user2"}),
            {"user1"},
            {"user1": UserDetail(id="user1", user_name="User 1", eppns=["test@eppn"], emails=["user1@example.com"])},
        ),
    ],
)
def test__get_repo_user_by_id(app, mocker: MockerFixture, repository_member, file_users_id, expected):
    mocker.patch(
        "server.services.users.search",
        return_value=SearchResponse[MapUser](
            total_results=1,
            start_index=0,
            items_per_page=20,
            resources=[
                MapUser(
                    id="user1",
                    user_name="User 1",
                    edu_person_principal_names=[EPPN(value="test@eppn")],
                    emails=[Email(value="user1@example.com")],
                )
            ],
        ),
    )
    result = bulks._get_repo_user_by_id(repository_member, file_users_id)  # noqa: SLF001
    assert result == expected


def test__build_check_results(app, mocker: MockerFixture):
    mocker.patch("server.services.bulks._check_immutable_attributes", return_value=None)
    update_user = [
        UserDetail(
            user_name="User 1",
            eppns=["test@eppn"],
            emails=["user1@example.com"],
            groups=[
                GroupSummary(id="group1", display_name="Group 1"),
            ],
        ),
        UserDetail(
            id="user2",
            user_name="User 2",
            eppns=["test@eppn"],
            emails=["user2@example.com"],
            groups=[GroupSummary(id="group1", display_name="Group 1")],
        ),
        UserDetail(id="user3", user_name="User 1", eppns=["test@eppn"], emails=["user1@example.com"]),
        UserDetail(id="not_repo_user", user_name="User 1", eppns=["test@eppn"], emails=["user1@example.com"]),
    ]
    create_user = [
        UserDetail(
            id="user4",
            user_name="User 4",
            eppns=["test@eppn"],
            emails=["user4@example.com"],
            groups=[
                GroupSummary(id="group4", display_name="Group 4"),
            ],
        ),
        UserDetail(user_name="User 5", eppns=["test@eppn"], emails=["user5@example.com"]),
        UserDetail(id="user6", user_name="User 6", eppns=["test@eppn"], emails=["user6@example.com"]),
    ]
    repository_member = RepositoryMember(groups={"group1", "group2"}, users={"user1", "user2"})
    repo_user_by_id = {
        "user1": UserDetail(id="user1", user_name="User 1", eppns=["test@eppn"], emails=["user1@example.com"]),
        "user2": UserDetail(
            id="user2",
            user_name="User 2",
            eppns=["test@eppn"],
            emails=["user2@example.com"],
            groups=[GroupSummary(id="group2", display_name="Group 2")],
        ),
        "user3": UserDetail(id="user3", user_name="User 3", eppns=["test@eppn"], emails=["user3@example.com"]),
    }
    expected_check_results = [
        CheckResult(
            id="user4",
            eppn=["test@eppn"],
            email=["user4@example.com"],
            user_name="User 4",
            groups={"group4"},
            status="error",
            code="Group ID does not exist",
        ),
        CheckResult(
            id=None,
            eppn=["test@eppn"],
            email=["user5@example.com"],
            user_name="User 5",
            groups=set(),
            status="error",
            code="Invalid user data",
        ),
        CheckResult(
            id="user6",
            eppn=["test@eppn"],
            email=["user6@example.com"],
            user_name="User 6",
            groups=set(),
            status="create",
            code=None,
        ),
        CheckResult(
            id="user2",
            eppn=["test@eppn"],
            email=["user2@example.com"],
            user_name="User 2",
            groups={"group1"},
            status="update",
            code=None,
        ),
        CheckResult(
            id="user3",
            eppn=["test@eppn"],
            email=["user1@example.com"],
            user_name="User 3",
            groups=set(),
            status="skip",
            code=None,
        ),
    ]
    expected_summary = HistorySummary(create=1, update=1, delete=0, skip=1, error=2)
    result = bulks._build_check_results(update_user, create_user, repository_member, repo_user_by_id)  # noqa: SLF001
    assert result == (expected_check_results, expected_summary)


@pytest.mark.parametrize(
    ("user_detail", "expected"),
    [
        (
            UserDetail(
                user_name="User 1",
                eppns=["test@eppn"],
                emails=["user1@example.com"],
            ),
            False,
        ),
        (
            UserDetail(
                id="invalid@id",
                user_name="User 1",
                eppns=["test@eppn"],
                emails=["user1@example.com"],
            ),
            False,
        ),
        (
            UserDetail(
                id="user1",
                user_name="User 1",
                eppns=["test@eppn"],
                emails=["user1@example.com"],
            ),
            True,
        ),
    ],
)
def test__check_value(app, mocker: MockerFixture, user_detail, expected):
    assert bulks._check_value(user_detail) == expected  # noqa: SLF001


@pytest.mark.parametrize(
    ("original", "update_user", "expected"),
    [
        (
            UserDetail(
                user_name="User 1",
                eppns=["test@eppn"],
                emails=["user1@example.com"],
                preferred_language="en",
                groups=[GroupSummary(id="group1", display_name="Group 1")],
            ),
            UserDetail(
                user_name="User 1",
                eppns=["test@eppn"],
                emails=["user1@example.com"],
                preferred_language="en",
                groups=[GroupSummary(id="group2", display_name="Group 2")],
            ),
            None,
        ),
        (
            UserDetail(
                user_name="User 1",
                eppns=["test@eppn"],
                emails=["user1@example.com"],
                preferred_language="en",
                groups=[GroupSummary(id="group1", display_name="Group 1")],
            ),
            UserDetail(
                user_name="User 2",
                eppns=["test@eppn"],
                emails=["user1@example.com"],
                preferred_language="en",
                groups=[GroupSummary(id="group2", display_name="Group 2")],
            ),
            "user_name is immutable",
        ),
        (
            UserDetail(
                user_name="User 1",
                eppns=["test@eppn"],
                emails=["user1@example.com"],
                preferred_language="en",
                groups=[GroupSummary(id="group1", display_name="Group 1")],
            ),
            UserDetail(
                user_name="User 1",
                eppns=["test2@eppn"],
                emails=["user1@example.com"],
                preferred_language="en",
                groups=[GroupSummary(id="group2", display_name="Group 2")],
            ),
            "eppns are immutable",
        ),
        (
            UserDetail(
                user_name="User 1",
                eppns=["test@eppn"],
                emails=["user1@example.com"],
                preferred_language="en",
                groups=[GroupSummary(id="group1", display_name="Group 1")],
            ),
            UserDetail(
                user_name="User 1",
                eppns=["test@eppn"],
                emails=["user2@example.com"],
                preferred_language="en",
                groups=[GroupSummary(id="group2", display_name="Group 2")],
            ),
            "emails are immutable",
        ),
        (
            UserDetail(
                user_name="User 1",
                eppns=["test@eppn"],
                emails=["user1@example.com"],
                preferred_language="en",
                groups=[GroupSummary(id="group1", display_name="Group 1")],
            ),
            UserDetail(
                user_name="User 1",
                eppns=["test@eppn"],
                emails=["user1@example.com"],
                preferred_language="ja",
                groups=[GroupSummary(id="group2", display_name="Group 2")],
            ),
            "preferred_language is immutable",
        ),
    ],
)
def test__check_immutable_attributes(app, mocker: MockerFixture, original, update_user, expected):
    assert bulks._check_immutable_attributes(original, update_user) == expected  # noqa: SLF001


def test_get_validate_result(app, mocker: MockerFixture):
    result = [
        {
            "id": "user1",
            "eppn": ["test@eppn"],
            "email": ["user1@example.com"],
            "user_name": "User 1",
            "groups": [],
            "status": "create",
            "code": None,
        }
    ]
    mocker.patch("server.services.history_table.get_paginated_upload_results", return_value=result)
    summary = HistorySummary(create=1, update=0, delete=0, skip=0, error=0)
    missing_user = []
    mocker.patch("server.services.history_table.get_upload_results", side_effect=[summary, missing_user])
    repository_member = RepositoryMember(groups={"group1"}, users={"user1"})
    mocker.patch("server.services.bulks.get_repository_member", return_value=repository_member)
    history_id = uuid7()
    status_filter = ["create"]
    offset = 1
    limit = 20
    expected = ValidateSummary(
        results=[
            CheckResult(
                id="user1",
                eppn=["test@eppn"],
                email=["user1@example.com"],
                user_name="User 1",
                groups=set(),
                status="create",
                code=None,
            )
        ],
        summary=summary,
        missing_user=missing_user,
        offset=offset,
        page_size=limit,
    )
    assert bulks.get_validate_result(history_id, status_filter, offset, limit) == expected


def test_update_users_success(app, mocker):
    history_id = uuid7()
    temp_file_id = uuid7()
    check_results = [
        CheckResult(id="user1", eppn=[], email=[], user_name="User 1", groups=set(), status="create", code=None)
    ]
    summary = {"error": 0}
    upload_data = mocker.MagicMock()
    upload_data.file.file_content = {"repositories": [{"id": "repo1"}]}
    upload_data.results = {"results": check_results, "summary": summary}
    mocker.patch("server.services.history_table.get_upload_by_id", return_value=upload_data)
    mocker.patch("server.services.bulks._build_bulk_operations_from_check_results", return_value=(["bulk_op"], 0))
    mocker.patch("server.services.bulks.save_file", return_value="file_id")
    mock_update_status = mocker.patch("server.services.history_table.update_upload_status")
    mocker.patch("server.services.history_table.delete_file_by_id")
    mocker.patch("server.services.bulks.get_access_token", return_value="token")
    mocker.patch("server.services.bulks.get_client_secret", return_value="secret")
    mocker.patch(
        "server.services.bulks.bulks.post",
        return_value=BulkResponse(operations=[BulkOperation(method="POST", path="/Users/user1", status="201")]),
    )

    result = bulks.update_users(history_id, temp_file_id, delete_users=None)

    assert result == history_id
    mock_update_status.assert_any_call(
        history_id=history_id,
        status="P",
        file_id="file_id",
        new_results={"results": check_results, "summary": {"error": 0, "delete": 0}},
    )
    mock_update_status.assert_any_call(
        history_id=history_id,
        status="S",
    )


def test_update_users_history_not_found(app, mocker):
    history_id = uuid7()
    temp_file_id = uuid7()
    mocker.patch("server.services.history_table.get_upload_by_id", return_value=None)
    with pytest.raises(ResourceNotFound) as exc:
        bulks.update_users(history_id, temp_file_id, delete_users=None)
    assert str(exc.value) == f"History not found: {history_id}"


def test_update_users_error_in_summary(app, mocker):
    history_id = uuid7()
    temp_file_id = uuid7()
    upload_data = mocker.MagicMock()
    upload_data.file.file_content = {"repositories": [{"id": "repo1"}]}
    upload_data.results = {"results": [], "summary": {"error": 1}}
    mocker.patch("server.services.history_table.get_upload_by_id", return_value=upload_data)
    with pytest.raises(ValueError) as exc:  # noqa: PT011
        bulks.update_users(history_id, temp_file_id, delete_users=None)
    assert str(exc.value) == "There are errors in the validation results."


def test_update_users_bulk_oauth_token_error(app, mocker):
    history_id = uuid7()
    temp_file_id = uuid7()
    check_results = [
        CheckResult(id="user1", eppn=[], email=[], user_name="User 1", groups=set(), status="create", code=None)
    ]
    summary = {"error": 0}
    upload_data = mocker.MagicMock()
    upload_data.file.file_content = {"repositories": [{"id": "repo1"}]}
    upload_data.results = {"results": check_results, "summary": summary}
    mocker.patch("server.services.history_table.get_upload_by_id", return_value=upload_data)
    mocker.patch("server.services.bulks._build_bulk_operations_from_check_results", return_value=(["bulk_op"], 0))
    mocker.patch("server.services.bulks.save_file", return_value="file_id")
    mocker.patch("server.services.history_table.update_upload_status", return_value=None)
    mocker.patch("server.services.history_table.delete_file_by_id")
    expected_error_message = "OAuth tokens are not stored on the server."
    mocker.patch("server.services.bulks.get_access_token", side_effect=OAuthTokenError(expected_error_message))
    with pytest.raises(OAuthTokenError) as exc:
        bulks.update_users(history_id, temp_file_id, delete_users=None)
    assert str(exc.value) == expected_error_message


def test_update_users_map_error(app, mocker):
    history_id = uuid7()
    temp_file_id = uuid7()
    check_results = [
        CheckResult(id="user1", eppn=[], email=[], user_name="User 1", groups=set(), status="create", code=None)
    ]
    summary = {"error": 0}
    upload_data = mocker.MagicMock()
    upload_data.file.file_content = {"repositories": [{"id": "repo1"}]}
    upload_data.results = {"results": check_results, "summary": summary}
    mocker.patch("server.services.history_table.get_upload_by_id", return_value=upload_data)
    mocker.patch("server.services.bulks._build_bulk_operations_from_check_results", return_value=(["bulk_op"], 0))
    mocker.patch("server.services.bulks.save_file", return_value="file_id")
    mocker.patch("server.services.history_table.update_upload_status")
    mocker.patch("server.services.history_table.delete_file_by_id")
    mocker.patch("server.services.bulks.get_access_token", return_value="token")
    mocker.patch("server.services.bulks.get_client_secret", return_value="secret")
    mocker.patch(
        "server.services.bulks.bulks.post",
        return_value=MapError(status="400", scim_type="invalidValue", detail="error"),
    )
    with pytest.raises(ResourceInvalid):
        bulks.update_users(history_id, temp_file_id, delete_users=None)


def test_update_users_failed(app, mocker):
    history_id = uuid7()
    temp_file_id = uuid7()
    check_results = [
        CheckResult(id="user1", eppn=[], email=[], user_name="User 1", groups=set(), status="create", code=None),
        CheckResult(id="user2", eppn=[], email=[], user_name="User 2", groups=set(), status="update", code=None),
    ]
    summary = {"error": 0}
    upload_data = mocker.MagicMock()
    upload_data.file.file_content = {"repositories": [{"id": "repo1"}]}
    upload_data.results = {"results": check_results, "summary": summary}
    mocker.patch("server.services.history_table.get_upload_by_id", return_value=upload_data)
    mocker.patch("server.services.bulks._build_bulk_operations_from_check_results", return_value=(["bulk_op"], 0))
    mocker.patch("server.services.bulks.save_file", return_value="file_id")
    mocker.patch("server.services.history_table.update_upload_status")
    mocker.patch("server.services.history_table.delete_file_by_id")
    mocker.patch("server.services.bulks.get_access_token", return_value="token")
    mocker.patch("server.services.bulks.get_client_secret", return_value="secret")
    mocker.patch(
        "server.services.bulks.bulks.post",
        return_value=BulkResponse(
            operations=[
                BulkOperation(method="POST", path="/Users/user1", status="201"),
                BulkOperation(method="POST", path="/Groups/group1", status="500"),
            ]
        ),
    )

    result = bulks.update_users(history_id, temp_file_id, delete_users=None)

    assert result == history_id


def test_save_file(app, mocker: MockerFixture):
    file_content = _FileContent(
        repositories=[{"id": "repo1", "serviceName": "test_service"}],
        groups=[{"id": "group1", "displayName": "Group 1"}, {"id": "group2", "displayName": "Group 2"}],
        users=[{"id": "user1", "userName": "User 1"}, {"id": "user2", "userName": "User 2"}],
    )
    file_path = "/var/tmp/jcgroups/test_file.csv"  # noqa: S108
    mock_get_file_by_id = mocker.patch(
        "server.services.history_table.get_file_by_id",
        return_value=mocker.MagicMock(file_content=file_content, file_path=file_path),
    )
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("server.services.history_table.create_file", return_value=None)
    mocker.patch("pathlib.Path.rename")
    return_fnc = mocker.patch("server.services.history_table.create_file", return_value=None)
    file_id = uuid7()
    bulks.save_file(file_id)
    mock_get_file_by_id.assert_called_once_with(file_id)
    return_fnc.assert_called_once()


def test_save_file_saved(app, mocker: MockerFixture):
    file_content = _FileContent(
        repositories=[{"id": "repo1", "serviceName": "test_service"}],
        groups=[{"id": "group1", "displayName": "Group 1"}, {"id": "group2", "displayName": "Group 2"}],
        users=[{"id": "user1", "userName": "User 1"}, {"id": "user2", "userName": "User 2"}],
    )
    mock_get_file_by_id = mocker.patch(
        "server.services.history_table.get_file_by_id", return_value=mocker.MagicMock(file_content=file_content)
    )
    mocker.patch("server.services.history_table.create_file", return_value=None)
    file_id = uuid7()
    bulks.save_file(file_id)
    mock_get_file_by_id.assert_called_once_with(file_id)


def test_save_file_with_exception(app, mocker: MockerFixture):
    file_id = uuid7()
    expected_error_message = f"File not found for file_id: {file_id}"
    mocker.patch("server.services.history_table.get_file_by_id", side_effect=RecordNotFound(expected_error_message))
    with pytest.raises(ResourceNotFound) as exc:
        bulks.save_file(file_id)
    assert str(exc.value) == expected_error_message


def test_save_file_not_found(app, mocker: MockerFixture):
    file_content = _FileContent(
        repositories=[{"id": "repo1", "serviceName": "test_service"}],
        groups=[{"id": "group1", "displayName": "Group 1"}, {"id": "group2", "displayName": "Group 2"}],
        users=[{"id": "user1", "userName": "User 1"}, {"id": "user2", "userName": "User 2"}],
    )
    file_path = "/var/tmp/jcgroups/test_file.csv"  # noqa: S108
    mock_get_file_by_id = mocker.patch(
        "server.services.history_table.get_file_by_id",
        return_value=mocker.MagicMock(file_content=file_content, file_path=file_path),
    )
    mocker.patch("server.services.history_table.create_file", return_value=None)
    file_id = uuid7()
    with pytest.raises(ResourceNotFound) as exc:
        bulks.save_file(file_id)
    mock_get_file_by_id.assert_called_once_with(file_id)
    assert str(exc.value) == f"File not found: {file_path}"


def test_save_file_invalid_suffix(app, mocker: MockerFixture):
    file_content = _FileContent(
        repositories=[{"id": "repo1", "serviceName": "test_service"}],
        groups=[{"id": "group1", "displayName": "Group 1"}, {"id": "group2", "displayName": "Group 2"}],
        users=[{"id": "user1", "userName": "User 1"}, {"id": "user2", "userName": "User 2"}],
    )
    file_path = "/var/tmp/jcgroups/test_file.css"  # noqa: S108
    mock_get_file_by_id = mocker.patch(
        "server.services.history_table.get_file_by_id",
        return_value=mocker.MagicMock(file_content=file_content, file_path=file_path),
    )
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("server.services.history_table.create_file", return_value=None)
    file_id = uuid7()
    with pytest.raises(ResourceInvalid) as exc:
        bulks.save_file(file_id)
    mock_get_file_by_id.assert_called_once_with(file_id)
    assert str(exc.value) == "not supported file format."


def test_build_map_user_from_check_result(app, mocker: MockerFixture):
    check_result = CheckResult(
        id="user1",
        eppn=["test@eppn"],
        email=["test@example.com"],
        user_name="User 1",
        groups={"group1", "group2"},
        status="create",
        code=None,
    )
    expected = MapUser(
        id="user1",
        user_name="User 1",
        edu_person_principal_names=[EPPN(value="test@eppn")],
        emails=[Email(value="test@example.com")],
        groups=[Group(value="group1"), Group(value="group2")],
    )
    result = bulks.build_map_user_from_check_result(check_result)
    assert result.id == expected.id
    assert result.user_name == expected.user_name
    assert_unordered_model_list_equal(result.edu_person_principal_names, expected.edu_person_principal_names)
    assert_unordered_model_list_equal(result.emails, expected.emails)
    assert_unordered_model_list_equal(result.groups, expected.groups)


def test_build_remove_user_path(app, mocker: MockerFixture):
    user = UserDetail(id="user1", user_name="User 1", eppns=["test@eppn"], emails=["test@example.com"])
    repository_id = "repo1"
    expected = BulkOperation(
        method="PATCH",
        bulk_id=None,
        path="Users/user1",
        data=RemoveOperation(path="groups[(value eq 'jc_repo1_gr_group1')]"),
        location=None,
        response=None,
        status=None,
    )
    mocker.patch(
        "server.services.utils.detect_affiliations",
        return_value=Affiliations(
            roles=[],
            groups=[_Group(repository_id=repository_id, group_id="jc_repo1_gr_group1", user_defined_id="group1")],
        ),
    )
    result = bulks.build_remove_user_path(user, repository_id)
    assert result == expected


def test__build_bulk_operations_from_check_results(app, mocker: MockerFixture):
    repository_id = "repo1"
    check_results = [
        CheckResult(
            id="user1",
            eppn=["test@eppn"],
            email=["test@example.com"],
            user_name="User 1",
            groups={"group1", "group2"},
            status="create",
            code=None,
        ),
        CheckResult(
            id="user2",
            eppn=["test@eppn"],
            email=["test2@example.com"],
            user_name="User 2",
            groups={"group1", "group2"},
            status="update",
            code=None,
        ),
        CheckResult(
            id="user3",
            eppn=["test@eppn"],
            email=["test3@example.com"],
            user_name="User 3",
            groups={"group1", "group2"},
            status="update",
            code=None,
        ),
    ]
    delete_users = ["user1"]
    expected = (
        [
            BulkOperation(
                method="POST",
                path="/Users",
                data=MapUser(
                    id="user1",
                    user_name="User 1",
                    edu_person_principal_names=[EPPN(value="test@eppn")],
                    emails=[Email(value="test@example.com")],
                    groups=[Group(value="group2"), Group(value="group1")],
                ),
            ),
            BulkOperation(
                method="POST",
                path="/Users",
                data=MapUser(
                    id="user1",
                    user_name="User 1",
                    edu_person_principal_names=[EPPN(value="test@eppn")],
                    emails=[Email(value="test@example.com")],
                    groups=[Group(value="group2"), Group(value="group1")],
                ),
            ),
        ],
        1,
    )
    mocker.patch(
        "server.services.bulks.get_repository_member",
        return_value=RepositoryMember(groups={"group1", "group2"}, users={"user1"}),
    )
    mocker.patch(
        "server.services.bulks._get_repo_user_by_id",
        return_value={
            "user2": UserDetail(
                id="user2",
                user_name="User 2",
                eppns=["test@eppn"],
                emails=["test@example.com"],
                groups=[GroupSummary(id="group3")],
            ),
        },
    )
    mocker.patch("server.services.bulks._build_groups_update_bulk_operations", return_value=[])
    mocker.patch(
        "server.services.users.search",
        return_value=SearchResponse[MapUser](
            total_results=0,
            start_index=0,
            items_per_page=20,
            resources=[
                MapUser(
                    id="user3",
                    user_name="User 3",
                    edu_person_principal_names=[EPPN(value="test@eppn")],
                    emails=[Email(value="test3@example.com")],
                ),
                MapUser(
                    user_name="User 4",
                    edu_person_principal_names=[EPPN(value="test@eppn")],
                    emails=[Email(value="test4@example.com")],
                ),
            ],
        ),
    )
    mocker.patch(
        "server.services.utils.detect_affiliations",
        return_value=Affiliations(
            roles=[],
            groups=[_Group(repository_id=repository_id, group_id="jc_repo1_gr_group1", user_defined_id="group1")],
        ),
    )
    result = bulks._build_bulk_operations_from_check_results(repository_id, check_results, delete_users)  # noqa: SLF001
    assert len(result[0]) == len(expected[0])
    for r, e in zip(result[0], expected[0], strict=False):
        assert r.method == e.method
        assert r.path == e.path
        assert isinstance(r.data, MapUser)
        assert isinstance(e.data, MapUser)
        assert r.data.id == e.data.id
        assert r.data.user_name == e.data.user_name
        assert_unordered_model_list_equal(r.data.edu_person_principal_names, e.data.edu_person_principal_names)
        assert_unordered_model_list_equal(r.data.emails, e.data.emails)
        assert_unordered_model_list_equal(r.data.groups, e.data.groups)
    assert result[1] == expected[1]


def test__build_groups_update_bulk_operations(app, mocker: MockerFixture):
    mocker.patch("server.services.users.get_system_admins", return_value={"admin1"})
    mocker.patch(
        "server.services.groups.get_by_id",
        return_value=MapGroup(
            id="jc_repo1_gr_group1",
            display_name="Group 1",
            members=[MemberUser(value="user1"), MemberUser(value="user2"), MemberGroup(value="group1")],
        ),
    )
    bulks._build_groups_update_bulk_operations({"group1": {"add": {"user1"}, "remove": {"user2", "user3"}}})  # noqa: SLF001


def test__build_groups_update_bulk_operations_no_group(app, mocker: MockerFixture):
    mocker.patch("server.services.users.get_system_admins", return_value={"admin1"})
    mocker.patch("server.services.groups.get_by_id", side_effect=None)
    result = bulks._build_groups_update_bulk_operations({"group1": {"add": set(), "remove": set()}})  # noqa: SLF001
    assert result == [
        BulkOperation(
            method="PATCH",
            path="Groups/group1",
            data=AddOperation(op="add", path="members", value={"type": "User", "value": "admin1"}),
        )
    ]


def test_get_upload_result(app, mocker: MockerFixture):
    history_id = uuid7()
    status_filter = ["create"]
    offset = 0
    size = 10
    file_id = uuid7()
    file_name = "test_file.csv"
    operator = "test_operator"
    start_timestamp = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    items = [
        CheckResult(
            id="user1",
            eppn=["test@eppn"],
            email=["test@example.com"],
            user_name="User 1",
            groups={"group1"},
            status="create",
            code=None,
        )
    ]
    mock_file = mocker.MagicMock(file_path="var/tmp/test_file.csv")
    upload = mocker.MagicMock(
        file_id=file_id, file=mock_file, operator_name=operator, timestamp=start_timestamp, end_timestamp=None
    )
    raw_results = [i.model_dump() for i in items]
    summary = HistorySummary(create=1, update=1, delete=0, skip=0, error=0)
    mocker.patch("server.services.history_table.get_upload_by_id", return_value=upload)
    mocker.patch("server.services.history_table.get_paginated_upload_results", return_value=raw_results)
    mocker.patch("server.services.history_table.get_upload_results", return_value=summary)

    result = bulks.get_upload_result(history_id, status_filter, offset, size)

    expected = ResultSummary(
        items=items,
        summary=summary,
        file_id=file_id,
        file_name=file_name,
        operator=operator,
        start_timestamp=start_timestamp,
        total=0,
        offset=offset,
        page_size=size,
    )
    assert result == expected


def test_get_upload_result_history_not_found(app, mocker: MockerFixture):
    history_id = uuid7()
    expected_error_message = f"upload history not found: {history_id}"
    mocker.patch("server.services.history_table.get_upload_by_id", return_value=None)
    with pytest.raises(RecordNotFound) as exc:
        bulks.get_upload_result(history_id, status_filter=["create"], offset=1, size=20)
    assert str(exc.value) == expected_error_message


@pytest.mark.parametrize(
    ("file_path", "file_exist"),
    [
        ("/var/tmp/test_file.csv", True),  # noqa: S108
        ("/var/tmp/test_file.csv", False),  # noqa: S108
    ],
)
def test_delete_temporary_file(app, mocker: MockerFixture, file_path, file_exist):
    file_id = uuid7()
    mocker.patch("server.services.history_table.get_file_by_id", return_value=mocker.MagicMock(file_path=file_path))
    mocker.patch("pathlib.Path.exists", return_value=file_exist)
    mocker.patch("pathlib.Path.unlink")
    mocker.patch("server.services.history_table.delete_file_by_id")
    bulks.delete_temporary_file(str(file_id))


def test_delete_temporary_file_with_exception(app, mocker: MockerFixture):
    file_id = uuid7()
    mocker.patch("server.services.history_table.get_file_by_id", side_effect=RecordNotFound(""))
    assert bulks.delete_temporary_file(str(file_id)) is None
