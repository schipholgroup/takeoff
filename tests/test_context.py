import pytest

from takeoff.context import Context


@pytest.fixture(scope='module', autouse=True)
def clear():
    Context().clear()


def test_create():
    Context().create_or_update("Alice", "Cooper")
    assert Context().get("Alice") == "Cooper"


def test_update():
    Context().create_or_update("Alice", "Cooper")
    assert Context().get("Alice") == "Cooper"
    Context().create_or_update("Alice", "da Man")
    assert Context().get("Alice") == "da Man"


def test_exists():
    Context().create_or_update("Alice", "Cooper")
    assert Context().exists("Alice")


def test_clear():
    Context().create_or_update("Alice", "Cooper")
    Context().clear()
    assert not Context().exists("Alice")


def test_delete():
    Context().create_or_update("Alice", "Cooper")
    Context().create_or_update("James", "Hetfield")
    assert Context().exists("Alice")
    assert Context().exists("James")

    Context().delete("Alice")
    assert not Context().exists("Alice")
    assert Context().exists("James")


def test_get_or_else():
    Context().create_or_update("Alice", "Cooper")
    assert Context().get_or_else("Not exists", {}) == {}
    assert Context().get_or_else("Alice", {}) == "Cooper"
