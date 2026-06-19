import pytest
from library.main import DatabaseConnection, DatabaseAdapter, Factory


def test_user_borrow_book():
    db = DatabaseConnection(":memory:")
    adapter = DatabaseAdapter(db)
    factory = Factory(adapter)

    admin = factory.create_user("admin", "123", "Adam", "Smith", "admin", True)
    admin.add_book("Harry Potter", "JKR", 1999, "Fantasy", 1000)

    user = factory.create_user("Jane", "1324", "Jane", "Smith", "user", True)
    user.borrow_book("Harry Potter", "JKR")

    result = adapter.select(["username", "title"], "in_possession")
    assert result == [("Jane", "Harry Potter")]
