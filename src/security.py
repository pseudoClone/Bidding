from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

load_dotenv()

ALGORITHM = str(os.getenv("ALGORITHM"))
SECRET_KEY = str(os.getenv("SECRET_KEY"))
ACCESS_TOKEN_EXPIRES_IN = int(str(os.getenv("ACCESS_TOKEN_EXPIRES_IN")))

passwordContext = CryptContext(schemes=["bcrypt"])


def verifyPassword(plaintext: str, hashed: str) -> bool:
    return passwordContext.verify(plaintext, hashed)


def getPasswordHash(password: str) -> str:
    return passwordContext.hash(password)


def createAccessToken(data: dict, expiresDelta: timedelta | None = None):
    toEncode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expiresDelta or timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN)
    )
    toEncode.update({"exp": expire})
    return jwt.encode(toEncode, SECRET_KEY, algorithm=ALGORITHM)
