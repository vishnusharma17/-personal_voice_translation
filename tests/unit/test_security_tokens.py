"""
Unit Tests: Security Tokens
"""

from backend.core.security import create_access_token, verify_access_token


def test_token_creation_and_verification():
    token = create_access_token(user_id="usr_test_1", display_name="Test User")
    assert token is not None
    assert isinstance(token, str)

    payload = verify_access_token(token)
    assert payload is not None
    assert payload["sub"] == "usr_test_1"
    assert payload["name"] == "Test User"


def test_invalid_token_verification():
    payload = verify_access_token("invalid.token.structure")
    assert payload is None
