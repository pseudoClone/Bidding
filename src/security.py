from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from dotenv import load_dotenv
import os
import jwt
from jwt import PyJWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from .main import get_session
from .model import User

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


oauth2Scheme = OAuth2PasswordBearer(tokenUrl="token")


def getCurrentUser(
    token: str = Depends(oauth2Scheme), session: Session = Depends(get_session)
) -> User:
    credentialsException = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="You are not authorized to do this",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        userID = payload.get("sub")
        if userID is None:
            raise credentialsException
    except PyJWTError:
        raise credentialsException

    user = session.get(User, userID)
    if user is None:
        raise credentialsException
    return user
