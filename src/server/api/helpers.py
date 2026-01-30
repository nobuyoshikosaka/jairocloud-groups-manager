#
# Copyright (C) 2025 National Institute of Informatics.
#

"""Provides helpers for API endpoints."""

import traceback
import typing as t

from functools import wraps

from flask import jsonify, make_response, request
from flask_pydantic.core import _sanitize_ctx_errors  # noqa: PLC2701
from pydantic import BaseModel, ValidationError
from werkzeug.datastructures import FileStorage

from server.config import config


def validate_files(func: t.Callable) -> t.Callable:  # noqa: C901
    """Decorator to validate file uploads in Flask routes.

    Args:
        func (t.Callable): The Flask route function to be decorated.

    Returns:
        t.Callable: The decorated function with file validation.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        fl, err = None, {}

        files_in_kwargs = func.__annotations__.get("files")
        if files_in_kwargs and issubclass(files_in_kwargs, BaseModel):
            files_model = files_in_kwargs
            file_params = {}

            for field_name, field_info in files_model.model_fields.items():
                if field_name not in request.files:
                    continue

                origin = t.get_origin(field_info.annotation)
                uploaded_files = (
                    request.files.getlist(field_name)
                    if origin is list
                    else [request.files.get(field_name)]
                )

                size_errors = _check_file_size(field_name, *uploaded_files)
                if size_errors:
                    if "file_size" not in err:
                        err["file_size"] = []
                    err["file_size"].extend(size_errors)

                file_params[field_name] = (
                    uploaded_files if origin is list else uploaded_files[0]
                )

            if err:
                return make_response(jsonify({"validation_error": err}), 400)

            try:
                fl = files_model(**file_params)
            except ValidationError as exc:
                traceback.print_exc()
                err["file_params"] = _sanitize_ctx_errors(exc.errors())

        if err:
            return make_response(jsonify({"validation_error": err}), 400)

        if files_in_kwargs:
            kwargs["files"] = fl

        return func(*args, **kwargs)

    return wrapper


def _check_file_size(field_name: str, *files: FileStorage | None) -> list:
    max_size = config.API.max_upload_size
    errors = []
    for file_storage in files:
        if not file_storage:
            continue

        file_storage.seek(0, 2)
        file_length = file_storage.tell()
        file_storage.seek(0)

        if file_length > max_size:
            errors.append({
                "loc": [field_name],
                "msg": f"File size exceeds limit of {max_size} bytes",
                "type": "value_error.filesize_limit",
                "ctx": {"limit_value": max_size, "actual_value": file_length},
            })
    return errors
