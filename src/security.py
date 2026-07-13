from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from dotenv import load_dotenv
import os
import jwt

load_dotenv()

ALGORITHM = str(os.getenv("ALGORITHM"))
SECRET_KEY = str(os.getenv("SECRET_KEY"))
ACCESS_TOKEN_EXPIRES_IN = int(str(os.getenv("ACCESS_TOKEN_EXPIRES_IN")))

passwordHash = PasswordHash.recommended()
"""
https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#hash-and-verify-the-passwords
"""


def verifyPassword(plaintext: str, hashed: str) -> bool:
    return passwordHash.verify(plaintext, hashed)


def getPasswordHash(password: str) -> str:
    return passwordHash.hash(password)


def createAccessToken(data: dict, expiresDelta: timedelta | None = None):
    toEncode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expiresDelta or timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN)
    )
    toEncode.update({"exp": expire})
    return jwt.encode(toEncode, SECRET_KEY, algorithm=ALGORITHM)
