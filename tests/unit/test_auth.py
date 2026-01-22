import pytest

from flask import make_response, redirect

from server.api import auth


@pytest.fixture
def test_login():
    assert auth.login() == make_response(redirect("/?error=401"))
