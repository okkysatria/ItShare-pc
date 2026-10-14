"""
core/credentials.py - Cryptographic username and password generator.
"""
import secrets
import string

def generate_username(length: int = 8) -> str:
    """
    Generate random lowercase alphanumeric username of specified length (default 8).
    Always starts with a letter.
    """
    if length < 2:
        raise ValueError("Username length must be at least 2 characters")
    letters = string.ascii_lowercase
    digits = string.digits
    first_char = secrets.choice(letters)
    rest = [secrets.choice(letters + digits) for _ in range(length - 1)]
    return first_char + "".join(rest)

def generate_password(length: int = 16) -> str:
    """
    Generate random alphanumeric password of specified length (default 16).
    Guarantees combination of uppercase, lowercase, and digits.
    Uses secrets module for cryptographically secure randomness.
    Does NOT log the password.
    """
    if length < 4:
        raise ValueError("Password length must be at least 4 characters")

    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    alphabet = uppercase + lowercase + digits

    mandatory = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits)
    ]
    remaining = [secrets.choice(alphabet) for _ in range(length - len(mandatory))]
    password_chars = mandatory + remaining

    for i in range(len(password_chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

    return "".join(password_chars)
