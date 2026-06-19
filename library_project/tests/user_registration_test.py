from library.main import Factory, DatabaseAdapter, DatabaseConnection
import pytest


def test_register_user():
    db = DatabaseConnection(":memory:")
    adapter = DatabaseAdapter(db)
    factory = Factory(adapter)

    user = factory.create_user(
        "john",
        "1234",
        "John",
        "Smith",
        "user",
        True
    )

    users = adapter.select(["username"], "users")

    assert users == [("john",)]