from typing import Generator, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlmodel import Session

from app.core.config import settings
from app.domain.models.user import User
from app.infrastructure.database.session import get_session
from app.infrastructure.database.postgres_repo import PostgresRepository

# Định nghĩa scheme auth (Bearer Token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# Dependency lấy Repository (giúp code gọn hơn)
def get_repository(session: Session = Depends(get_session)) -> PostgresRepository:
    return PostgresRepository(session)

# Dependency lấy User hiện tại từ Token
def get_current_user(
    token: str = Depends(oauth2_scheme),
    repo: PostgresRepository = Depends(get_repository)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = repo.get_user_by_email(email)
    if user is None:
        raise credentials_exception
    return user