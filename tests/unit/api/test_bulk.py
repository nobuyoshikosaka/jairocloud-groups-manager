import inspect
import typing as t

from datetime import UTC, datetime
from http import HTTPStatus
from uuid import UUID, uuid7

from flask_login import login_user
from redis.exceptions import ConnectionError as RedisConnectionError

from server.api import bulk
from server.api.schemas import BulkBody, ErrorResponse, ExcuteRequest, TargetRepository, UploadQuery
from server.entities.bulk import HistorySummary, ResultSummary, ValidateSummary
from server.entities.login_user import LoginUser
from server.exc import InvalidRecordError, RecordNotFound


if t.TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_upload_file(app, mocker: MockerFixture):
    test_func = inspect.unwrap(bulk.upload_file)
    repository_id = "repo123"
    operator_id = "user123"
    operator_name = "test_user"
    mock_user = LoginUser(eppn="test_eppn", is_member_of="", user_name=operator_name, map_id=operator_id, session_id="")
    form = TargetRepository(repository_id=repository_id)
    dummy_file = mocker.Mock(bulk_file=mocker.Mock(filename="test.csv", save=mocker.Mock()))
    mock_task = mocker.Mock(id="task_id")
    mock_create_file = mocker.patch("server.services.history_table.create_file", return_value=None)
    mock_delete_temporary_file = mocker.patch(
        "server.services.bulks.delete_temporary_file.apply_async", return_value=None
    )
    mock_validate_upload_data = mocker.patch(
        "server.services.bulks.validate_upload_data.apply_async", return_value=mock_task
    )
    with app.test_request_context():
        login_user(mock_user)
        result = test_func(form=form, files=dummy_file)
        assert result[0].task_id == mock_task.id
        assert isinstance(result[0], BulkBody)
        assert result[1] == HTTPStatus.OK
        _, kwargs = mock_create_file.call_args
        assert isinstance(kwargs["file_id"], UUID)
        assert isinstance(kwargs["file_path"], str)
        assert kwargs["file_content"] == {"repositories": [{"id": repository_id}]}
        args, kwargs = mock_delete_temporary_file.call_args
        assert isinstance(args[0][0], str)
        assert isinstance(kwargs["countdown"], int)
        args, kwargs = mock_validate_upload_data.call_args
        assert args[0][0] == operator_id
        assert args[0][1] == operator_name
        assert isinstance(args[0][2], UUID)


def test_validate_status(app, mocker: MockerFixture):
    task_id = "task_id"
    test_func = inspect.unwrap(bulk.validate_status)
    mock_task = mocker.Mock()
    mock_task.state = "SUCCESS"
    mocker.patch("server.services.bulks.validate_upload_data.AsyncResult", return_value=mock_task)
    expected = BulkBody(status=mock_task.state)
    with app.test_request_context():
        result = test_func(task_id)
        assert result[0] == expected
        assert result[1] == HTTPStatus.OK


def test_validate_status_not_found(app, mocker: MockerFixture):
    task_id = "task_id"
    test_func = inspect.unwrap(bulk.validate_status)
    mocker.patch("server.services.bulks.validate_upload_data.AsyncResult", return_value=None)
    with app.test_request_context():
        result = test_func(task_id)
        assert result[0] == ErrorResponse(code="", message="Task not found: task_id")
        assert result[1] == HTTPStatus.NOT_FOUND


def test_validate_status_redis_error(app, mocker: MockerFixture):
    task_id = "task_id"
    test_func = inspect.unwrap(bulk.validate_status)
    mocker.patch("server.services.bulks.validate_upload_data.AsyncResult", side_effect=RedisConnectionError)
    with app.test_request_context():
        result = test_func(task_id)
        assert result[0] == ErrorResponse(code="", message=f"Failed to connect to Redis: {task_id}")
        assert result[1] == HTTPStatus.INTERNAL_SERVER_ERROR


def test_validate_result(app, mocker: MockerFixture):
    task_id = "task_id"
    history_id = uuid7()
    test_func = inspect.unwrap(bulk.validate_result)
    mock_task = mocker.Mock()
    mock_task.result = history_id
    mocker.patch("server.services.bulks.validate_upload_data.AsyncResult", return_value=mock_task)
    expected = ValidateSummary(
        results=[],
        summary=HistorySummary(create=0, delete=0, error=0, skip=0, update=0),
        missing_user=[],
        offset=1,
        page_size=50,
    )
    mock_validate_result = mocker.patch("server.services.bulks.get_validate_result", return_value=expected)
    with app.test_request_context():
        result = test_func(query=UploadQuery(f=[3], p=2, l=50), task_id=task_id)
        assert result[0] == expected
        assert result[1] == HTTPStatus.OK
        mock_validate_result.assert_called_once_with(history_id=history_id, status_filter=["skip"], offset=2, size=50)


def test_validate_result_failed(app, mocker: MockerFixture):
    task_id = "task_id"
    test_func = inspect.unwrap(bulk.validate_result)
    mock_task = mocker.Mock()
    mock_task.successful.return_value = False
    mocker.patch("server.services.bulks.validate_upload_data.AsyncResult", return_value=mock_task)
    with app.test_request_context():
        result = test_func(query=UploadQuery(), task_id=task_id)
        assert result[0] == ErrorResponse(code="", message=f"Task not successful: {task_id}")
        assert result[1] == HTTPStatus.BAD_REQUEST


def test_validate_result_not_found(app, mocker: MockerFixture):
    task_id = "task_id"
    test_func = inspect.unwrap(bulk.validate_result)
    mocker.patch("server.services.bulks.validate_upload_data.AsyncResult", return_value=None)
    with app.test_request_context():
        result = test_func(query=UploadQuery(), task_id=task_id)
        assert result[0] == ErrorResponse(code="", message=f"Task not found: {task_id}")
        assert result[1] == HTTPStatus.NOT_FOUND


def test_validate_result_redis_error(app, mocker: MockerFixture):
    task_id = "task_id"
    test_func = inspect.unwrap(bulk.validate_result)
    mock_return_value = InvalidRecordError("Results must include 'summary' and 'results' keys")
    mocker.patch(
        "server.services.bulks.validate_upload_data.AsyncResult", return_value=mocker.Mock(result=mock_return_value)
    )
    with app.test_request_context():
        result = test_func(query=UploadQuery(), task_id=task_id)
        assert result[0] == ErrorResponse(code="", message=f"Task resulted in an exception: {mock_return_value}")
        assert result[1] == HTTPStatus.BAD_REQUEST


def test_validate_result_redis_connection_error(app, mocker: MockerFixture):
    task_id = "task_id"
    test_func = inspect.unwrap(bulk.validate_result)
    mocker.patch("server.services.bulks.validate_upload_data.AsyncResult", side_effect=RedisConnectionError)
    with app.test_request_context():
        result = test_func(query=UploadQuery(), task_id=task_id)
        assert result[0] == ErrorResponse(code="", message=f"Failed to connect to Redis: {task_id}")
        assert result[1] == HTTPStatus.INTERNAL_SERVER_ERROR


def test_execute(app, mocker: MockerFixture):
    test_func = inspect.unwrap(bulk.execute)
    temp_id = uuid7()
    repository_id = "repo1"
    task_id = "task_id"
    body = ExcuteRequest(
        temp_file_id=temp_id,
        repository_id=repository_id,
        delete_users=["user1", "user2"],
    )
    history_id = uuid7()
    mock_get_history_by_file_id = mocker.patch(
        "server.services.history_table.get_history_by_file_id", return_value=mocker.Mock(id=history_id)
    )
    mock_execute_bulk_upload = mocker.patch(
        "server.services.bulks.update_users.apply_async", return_value=mocker.Mock(id=task_id)
    )
    expected = BulkBody(task_id=task_id, history_id=history_id)
    with app.test_request_context():
        result = test_func(body)
        assert result[0] == expected
        assert result[1] == HTTPStatus.OK
        mock_get_history_by_file_id.assert_called_once_with(temp_id)
        mock_execute_bulk_upload.assert_called_once_with(
            kwargs={"history_id": history_id, "temp_file_id": body.temp_file_id, "delete_users": body.delete_users}
        )


def test_execute_history_not_found(app, mocker: MockerFixture):
    test_func = inspect.unwrap(bulk.execute)
    temp_id = uuid7()
    body = ExcuteRequest(temp_file_id=temp_id)
    mocker.patch(
        "server.services.history_table.get_history_by_file_id", side_effect=RecordNotFound("History not found")
    )
    expected_message = "History not found"
    with app.test_request_context():
        result = test_func(body)
        assert result[0] == ErrorResponse(code="", message=expected_message)
        assert result[1] == HTTPStatus.NOT_FOUND


def test_execute_status(app, mocker: MockerFixture):
    test_func = inspect.unwrap(bulk.execute_status)
    task_id = "task_id"
    mocker.patch("server.services.bulks.update_users.AsyncResult", return_value=mocker.Mock(state="SUCCESS"))
    expected = BulkBody(status="SUCCESS")
    with app.test_request_context():
        result = test_func(task_id)
        assert result[0] == expected
        assert result[1] == HTTPStatus.OK


def test_execute_status_not_found(app, mocker: MockerFixture):
    test_func = inspect.unwrap(bulk.execute_status)
    task_id = "task_id"
    mocker.patch("server.services.bulks.update_users.AsyncResult", return_value=None)
    expected_message = "Task not found: task_id"
    with app.test_request_context():
        result = test_func(task_id)
        assert result[0] == ErrorResponse(code="", message=expected_message)
        assert result[1] == HTTPStatus.NOT_FOUND


def test_execute_status_redis_error(app, mocker: MockerFixture):
    test_func = inspect.unwrap(bulk.execute_status)
    task_id = "task_id"
    mocker.patch("server.services.bulks.update_users.AsyncResult", side_effect=RedisConnectionError)
    expected_message = f"Failed to connect to Redis: {task_id}"
    with app.test_request_context():
        result = test_func(task_id)
        assert result[0] == ErrorResponse(code="", message=expected_message)
        assert result[1] == HTTPStatus.INTERNAL_SERVER_ERROR


def test_result(app, mocker: MockerFixture):
    test_func = inspect.unwrap(bulk.result)
    history_id = uuid7()
    expected_summary = ResultSummary(
        items=[],
        summary=HistorySummary(create=0, delete=0, error=0, skip=0, update=0),
        file_id=uuid7(),
        file_name="",
        operator="",
        start_timestamp=datetime.now(UTC),
        end_timestamp=None,
        total=0,
        offset=2,
        page_size=50,
    )
    mock_get_upload_result = mocker.patch("server.services.bulks.get_upload_result", return_value=expected_summary)
    with app.test_request_context():
        result = test_func(history_id, UploadQuery(f=[0, 1], p=2, l=50))
        assert result[0] == expected_summary
        assert result[1] == HTTPStatus.OK
        mock_get_upload_result.assert_called_once_with(
            history_id=history_id, status_filter=["create", "update"], offset=2, size=50
        )


def test_result_not_found(app, mocker: MockerFixture):
    test_func = inspect.unwrap(bulk.result)
    history_id = uuid7()
    mocker.patch("server.services.bulks.get_upload_result", side_effect=RecordNotFound("History not found"))
    expected_message = "History not found"
    with app.test_request_context():
        result = test_func(history_id, UploadQuery())
        assert result[0] == ErrorResponse(code="", message=expected_message)
        assert result[1] == HTTPStatus.NOT_FOUND
