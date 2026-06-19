import pytest
from library.main import DatabaseConnection, DatabaseAdapter, Factory


def test_admin_add_book():
    db = DatabaseConnection(":memory:")
    adapter = DatabaseAdapter(db)
    factory = Factory(adapter)

    admin = factory.create_user("admin", "123", "Adam", "Smith", "admin", True)
    admin.add_book("Harry Potter", "JKR", 1999, "Fantasy", 1000)
    books = adapter.select(["title"], "books")
    assert books == [("Harry Potter",)]
