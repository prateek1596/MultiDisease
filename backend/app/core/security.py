"""
JWT authentication and password utilities.

Works with ANY version of bcrypt installed.
Falls back to hashlib-pbkdf2 if bcrypt is unavailable (dev only).
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ── Try to import bcrypt directly (bypasses passlib entirely) ─────────────────
try:
    import bcrypt as _bcrypt
    _USE_BCRYPT = True
except ImportError:
    _USE_BCRYPT = False

# ── Fallback: use werkzeug if available ───────────────────────────────────────
try:
    from werkzeug.security import generate_password_hash as _wk_hash
    from werkzeug.security import check_password_hash as _wk_check
    _USE_WERKZEUG = True
except ImportError:
    _USE_WERKZEUG = False


def get_password_hash(password: str) -> str:
    """Hash a password — tries bcrypt first, then werkzeug, then pbkdf2."""
    if _USE_BCRYPT:
        salt = _bcrypt.gensalt(rounds=12)
        return _bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    if _USE_WERKZEUG:
        return _wk_hash(password, method="pbkdf2:sha256", salt_length=16)
    # Pure-stdlib fallback
    return _pbkdf2_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        if _USE_BCRYPT and hashed_password.startswith("$2"):
            return _bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        if _USE_WERKZEUG and not hashed_password.startswith("$2"):
            return _wk_check(hashed_password, plain_password)
        if hashed_password.startswith("$2") and _USE_BCRYPT:
            return _bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        # stdlib fallback
        return _pbkdf2_verify(plain_password, hashed_password)
    except Exception:
        return False


# ── Pure-stdlib pbkdf2 fallback (no extra packages needed) ───────────────────
import hashlib, os, hmac

def _pbkdf2_hash(password: str) -> str:
    salt = os.urandom(16).hex()
    dk   = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000)
    return f"pbkdf2$sha256$260000${salt}${dk.hex()}"

def _pbkdf2_verify(plain: str, stored: str) -> bool:
    try:
        _, algo, iters, salt, dk_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac(algo, plain.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire    = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)):
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise exc
    return payload


async def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
