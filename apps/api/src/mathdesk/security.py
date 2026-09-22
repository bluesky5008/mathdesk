from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()

# 존재하지 않는 계정에도 같은 비용을 치러 사용자 열거를 막는다.
_DUMMY_HASH = _hasher.hash("mathdesk-dummy-password")

UNUSABLE_PASSWORD = "!"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
