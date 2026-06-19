import pytest
from library.main import DatabaseConnection, DatabaseAdapter, Factory


def test_admin_cannot_borrow():
    db = DatabaseConnection(":memory:")
    adapter = DatabaseAdapter(db)
    factory = Factory(adapter)

    admin = factory.create_user("admin", "123", "Adam", "Smith", "admin", True)

    with pytest.raises(RuntimeError):
        admin.borrow_book("Harry Potter", "JKR")
