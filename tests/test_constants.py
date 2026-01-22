"""Tests for libs/constants.py environment variable parsing."""

import os
from unittest import mock

import pytest


def test_get_env_str_returns_value() -> None:
    """Test that get_env_str returns the environment variable value."""
    with mock.patch.dict(os.environ, {"TEST_VAR": "test_value"}):
        # Import inside test to get fresh module state
        from libs.constants import get_env_str

        assert get_env_str("TEST_VAR") == "test_value"


def test_get_env_str_returns_default() -> None:
    """Test that get_env_str returns default when var is missing."""
    from libs.constants import get_env_str

    # Ensure the var doesn't exist
    os.environ.pop("NONEXISTENT_VAR", None)
    assert get_env_str("NONEXISTENT_VAR", "default") == "default"


def test_get_env_str_exits_when_missing_no_default() -> None:
    """Test that get_env_str exits when var is missing and no default."""
    from libs.constants import get_env_str

    os.environ.pop("NONEXISTENT_VAR", None)
    with pytest.raises(SystemExit):
        get_env_str("NONEXISTENT_VAR")


def test_get_env_int_returns_integer() -> None:
    """Test that get_env_int returns an integer."""
    with mock.patch.dict(os.environ, {"TEST_INT": "42"}):
        from libs.constants import get_env_int

        assert get_env_int("TEST_INT") == 42


def test_get_env_int_exits_on_non_integer() -> None:
    """Test that get_env_int exits when value is not an integer."""
    with mock.patch.dict(os.environ, {"TEST_INT": "not_an_int"}):
        from libs.constants import get_env_int

        with pytest.raises(SystemExit):
            get_env_int("TEST_INT")


def test_get_env_bool_returns_true() -> None:
    """Test that get_env_bool returns True for 'true'."""
    with mock.patch.dict(os.environ, {"TEST_BOOL": "true"}):
        from libs.constants import get_env_bool

        assert get_env_bool("TEST_BOOL") is True


def test_get_env_bool_returns_false() -> None:
    """Test that get_env_bool returns False for 'false'."""
    with mock.patch.dict(os.environ, {"TEST_BOOL": "false"}):
        from libs.constants import get_env_bool

        assert get_env_bool("TEST_BOOL") is False


def test_get_env_bool_case_insensitive() -> None:
    """Test that get_env_bool is case insensitive."""
    with mock.patch.dict(os.environ, {"TEST_BOOL": "TRUE"}):
        from libs.constants import get_env_bool

        assert get_env_bool("TEST_BOOL") is True


def test_get_env_bool_exits_on_invalid() -> None:
    """Test that get_env_bool exits on invalid value."""
    with mock.patch.dict(os.environ, {"TEST_BOOL": "yes"}):
        from libs.constants import get_env_bool

        with pytest.raises(SystemExit):
            get_env_bool("TEST_BOOL")
