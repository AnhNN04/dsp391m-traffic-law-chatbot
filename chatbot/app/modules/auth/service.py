from fastapi import HTTPException, status
from app.domain.models.user import User
from app.infrastructure.database.postgres_repo import PostgresRepository
from app.core.security import get_password_hash, verify_password, create_access_token
from app.domain.schemas.auth_dto import UserCreate, UserLogin, Token

class AuthService:
    def __init__(self, repo: PostgresRepository):
        self.repo = repo

    def register_user(self, user_in: UserCreate) -> User:
        # 1. Check if email exists
        if self.repo.get_user_by_email(user_in.email):
            raise HTTPException(
                status_code=400,
                detail="Email này đã được đăng ký."
            )
        
        # 2. Hash password & Save
        user = User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            full_name=user_in.full_name
        )
        return self.repo.create_user(user)

    def authenticate_user(self, login_data: UserLogin) -> Token:
        # 1. Get user
        user = self.repo.get_user_by_email(login_data.email)
        if not user:
            raise HTTPException(status_code=400, detail="Email hoặc mật khẩu không đúng.")
        
        # 2. Verify password
        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Email hoặc mật khẩu không đúng.")
        
        # 3. Create Token
        access_token = create_access_token(subject=user.email)
        return Token(access_token=access_token, token_type="bearer")