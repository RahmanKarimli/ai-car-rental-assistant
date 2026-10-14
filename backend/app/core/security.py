import hashlib
import hmac
import json
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

passwords = PasswordHasher()
def token() -> str:
    return secrets.token_urlsafe(32)
def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
def sign(value, key: str) -> str:
    return hmac.new(key.encode(), canonical(value).encode(), hashlib.sha256).hexdigest()
def verify_password(password: str, hashed: str) -> bool:
    try:
        return passwords.verify(hashed, password)
    except VerificationError:
        return False
