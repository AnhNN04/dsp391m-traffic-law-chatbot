from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from app.domain.schemas.auth_dto import UserCreate, UserResponse, Token, UserLogin
from app.infrastructure.database.postgres_repo import PostgresRepository
from app.modules.auth.service import AuthService
from app.api.v1.dependencies import get_repository, get_current_user
from app.domain.models.user import User

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(
    user_in: UserCreate,
    repo: PostgresRepository = Depends(get_repository)
):
    service = AuthService(repo)
    return service.register_user(user_in)

@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], # Hỗ trợ Swagger UI login
    repo: PostgresRepository = Depends(get_repository)
):
    # Swagger gửi username/password qua form data
    # Ta convert sang DTO của mình
    login_data = UserLogin(email=form_data.username, password=form_data.password)
    service = AuthService(repo)
    return service.authenticate_user(login_data)

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """API test để xem token có hoạt động không"""
    return current_user