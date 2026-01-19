from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True) # Foreign key logic xử lý tại tầng Service
    title: str = Field(default="New Chat")
    
    # Lưu toàn bộ lịch sử hội thoại dưới dạng JSON
    # Cấu trúc: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    history: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSONB))

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))