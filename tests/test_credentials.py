"""
tests/test_credentials.py - Unit tests for credential generation.
"""
import pytest
import string
from core.credentials import generate_username, generate_password

def test_generate_username_length_and_charset():
    user = generate_username(8)
    assert len(user) == 8
    assert user[0] in string.ascii_lowercase
    assert all(c in string.ascii_lowercase + string.digits for c in user)

def test_generate_password_length_and_charset():
    pwd = generate_password(16)
    assert len(pwd) == 16
    assert any(c in string.ascii_uppercase for c in pwd)
    assert any(c in string.ascii_lowercase for c in pwd)
    assert any(c in string.digits for c in pwd)
    assert all(c in string.ascii_letters + string.digits for c in pwd)

def test_credentials_uniqueness():
    users = {generate_username(8) for _ in range(1000)}
    assert len(users) == 1000

    passwords = {generate_password(16) for _ in range(1000)}
    assert len(passwords) == 1000

def test_invalid_lengths():
    with pytest.raises(ValueError):
        generate_username(1)
    with pytest.raises(ValueError):
        generate_password(3)
