from sqlmodel import create_engine, Session
from app.core.config import settings

# Tạo engine kết nối
# echo=True để hiện log câu lệnh SQL (tốt cho debug dev mode)
engine = create_engine(settings.DATABASE_URL, echo=True)

def get_session():
    """Dependency injection cho FastAPI"""
    with Session(engine) as session:
        yield session