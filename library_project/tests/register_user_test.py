from unittest.mock import patch
from library.main import DatabaseConnection, DatabaseAdapter, Factory, register_user


def test_register_user_inputs():
    db = DatabaseConnection(":memory:")
    adapter = DatabaseAdapter(db)
    factory = Factory(adapter)

    inputs = [
        "John",
        "Smith",
        "john",
        "1234",
        "user"
    ]

    with patch("builtins.input", side_effect=inputs):
        register_user(factory)

    users = adapter.select(["username"], "users")

    assert users == [("john",)]
