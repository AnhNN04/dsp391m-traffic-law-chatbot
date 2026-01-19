import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from contextlib import asynccontextmanager

from app.core.config import settings
from app.infrastructure.database.session import engine
from app.api.v1 import auth, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup (Dev mode)
    SQLModel.metadata.create_all(engine)
    yield
    # Shutdown (noop)


# Khởi tạo App
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Prod: set domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký Router
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
# app.include_router(chat.router, ...)

@app.get("/")
def root():
    return {"message": "Traffic Law Bot API is running!"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # Cấu hình lại host và port nếu cần
    # Sử dụng --reload chỉ trong môi trường phát triển
    