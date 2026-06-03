"""Security 单元测试 —— JWT + 密码哈希"""

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPassword:
    """密码哈希测试"""

    def test_hash_not_plaintext(self):
        hashed = hash_password("my_password_123")
        assert hashed != "my_password_123"
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_verify_correct(self):
        hashed = hash_password("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_verify_wrong(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2


class TestJWT:
    """JWT 令牌测试"""

    def test_create_and_decode(self):
        user_id = "test-user-123"
        token = create_access_token(user_id)
        decoded = decode_access_token(token)
        assert decoded == user_id

    def test_decode_invalid_token(self):
        result = decode_access_token("this.is.not.a.valid.token")
        assert result is None

    def test_decode_tampered_token(self):
        token = create_access_token("user-1")
        tampered = token + "x"
        result = decode_access_token(tampered)
        assert result is None

    def test_decode_expired_token(self):
        from jose import jwt as jose_jwt

        expired = jose_jwt.encode(
            {
                "sub": "user-1",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
                "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        result = decode_access_token(expired)
        assert result is None

    def test_different_users_different_tokens(self):
        t1 = create_access_token("user-a")
        t2 = create_access_token("user-b")
        assert t1 != t2

    def test_decode_returns_user_id(self):
        token = create_access_token("specific-user-id")
        assert decode_access_token(token) == "specific-user-id"
