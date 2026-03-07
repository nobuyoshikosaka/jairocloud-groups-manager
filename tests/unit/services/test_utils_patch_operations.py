import copy
import typing as t

import pytest

from pydantic import BaseModel

from server.entities.map_group import MapGroup
from server.entities.map_user import MapUser
from server.services.utils import patch_operations
from server.services.utils.patch_operations import (
    AddOperation,
    RemoveOperation,
    ReplaceOperation,
    _diff,
    _handle_list_diff,
    _handle_literal_diff,
)
from tests.helpers import load_json_data


def test_build_patch_operations_literal_diff() -> None:

    json_data_orig = load_json_data("data/map_group.json")
    orig = MapGroup.model_validate(json_data_orig)

    json_data_updated = load_json_data("data/map_group_update.json")
    updated = MapGroup.model_validate(json_data_updated)

    ops = patch_operations.build_patch_operations(orig, updated)

    expected_ops = [ReplaceOperation(op="replace", path="displayName", value="JAIRO test group UPDATED")]
    assert ops == expected_ops


def test_build_patch_operations_type_error() -> None:
    json_data_orig = load_json_data("data/map_group.json")
    orig = MapGroup.model_validate(json_data_orig)

    json_data_updated = load_json_data("data/map_user.json")
    updated = MapUser.model_validate(json_data_updated)
    error_msg = "Original and updated models must be of the same type."
    with pytest.raises(TypeError, match=error_msg):
        patch_operations.build_patch_operations(orig, updated)


def test_diff_with_include() -> None:
    json_data_orig = load_json_data("data/map_group.json")
    orig = MapGroup.model_validate(json_data_orig)

    updated = copy.deepcopy(orig)
    if updated.members and len(updated.members) > 0:
        updated.members[0].value = "changed_value"
    ops = _diff(orig, updated, include={"members"})
    assert all("members" in op.path for op in ops)


def test_diff_with_exclude() -> None:
    json_data_orig = load_json_data("data/map_group.json")
    orig = MapGroup.model_validate(json_data_orig)

    updated = copy.deepcopy(orig)
    if updated.members and len(updated.members) > 0:
        updated.members[0].value = "changed_value"
    ops = _diff(orig, updated, exclude={"members"})
    assert all("members" not in op.path for op in ops)


def test_handle_literal_diff_equal() -> None:

    result = _handle_literal_diff(1, 1, "a")
    assert result == []


def test_handle_literal_diff_add() -> None:
    expected_value = 5
    expected_path = "d"

    result = _handle_literal_diff(None, expected_value, expected_path)
    assert len(result) == 1
    assert isinstance(result[0], AddOperation)
    assert result[0].path == expected_path
    assert result[0].value == expected_value


def test_handle_literal_diff_remove() -> None:
    expected_path = "c"

    result = _handle_literal_diff(3, None, expected_path)
    assert len(result) == 1
    assert isinstance(result[0], RemoveOperation)
    assert result[0].path == expected_path


def test_handle_literal_diff_replace() -> None:
    expected_value = 5
    expected_path = "d"

    result = _handle_literal_diff(4, expected_value, expected_path)
    assert len(result) == 1
    assert isinstance(result[0], ReplaceOperation)
    assert result[0].path == expected_path
    assert result[0].value == expected_value


def test_handle_list_diff_diff() -> None:

    json_data_orig = load_json_data("data/map_group.json")
    orig_group = MapGroup.model_validate(json_data_orig)

    json_data_updated = load_json_data("data/map_group_update.json")
    updated_group = MapGroup.model_validate(json_data_updated)

    orig = [t.cast(BaseModel, m) for m in (orig_group.members or [])]
    updated = [t.cast(BaseModel, m) for m in (updated_group.members or [])]
    path = "members"
    result = _handle_list_diff(orig, updated, path)
    assert isinstance(result, list)


def test_handle_list_diff_identical() -> None:

    json_data_orig = load_json_data("data/map_group.json")
    orig_group = MapGroup.model_validate(json_data_orig)

    orig = [t.cast(BaseModel, m) for m in (orig_group.members or [])]
    updated = [t.cast(BaseModel, m) for m in (orig_group.members or [])]
    path = "members"
    result = _handle_list_diff(orig, updated, path)
    assert result == []


def test_build_update_member_operations() -> None:

    add = {"u1", "u2"}
    remove = {"u3", "u4"}
    user_list = {"u1", "u3"}
    system_admins = {"admin"}
    ops = patch_operations.build_update_member_operations(add, remove, user_list, system_admins)
    assert any(isinstance(op, patch_operations.AddOperation) and op.value["value"] in {"u2", "admin"} for op in ops)
    assert any(isinstance(op, patch_operations.RemoveOperation) and "u3" in op.path for op in ops)


def test_build_update_member_operations_add_update_system_admins() -> None:

    add = set()
    user_list = set()
    remove = set()
    system_admins = {"admin1", "admin2"}

    ops = patch_operations.build_update_member_operations(set(add), set(remove), set(user_list), set(system_admins))

    added_ids = {op.value["value"] for op in ops if isinstance(op, patch_operations.AddOperation)}
    assert "admin1" in added_ids
    assert "admin2" in added_ids
