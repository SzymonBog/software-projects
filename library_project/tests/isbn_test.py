from library.main import generate_isbn
import pytest


def test_generate_isbn():
    isbn = generate_isbn()

    assert len(isbn) == 13
    assert isbn.startswith("978")
