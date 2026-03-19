"""
Mongo History Implementation

Concrete implementation of IChatHistory using MongoDB.
Manages conversation logs and retrieves LangGraph checkpoints.

Author: AnhNN217-FHN
"""

from typing import List, Dict, Any, Optional
from pymongo import MongoClient, errors
from pymongo.collection import Collection

from app.domain.interfaces.i_chat_history import IChatHistory
from app.infrastructure.config import settings
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)


class MongoHistory(IChatHistory):
    """
    Adapter for MongoDB persistence.
    Handles 'conversations' collection for chat logs and 'checkpoints' for Agent state.
    """

    def __init__(self):
        """
        Initialize MongoDB Client and Collections.
        """
        try:
            self.client = MongoClient(settings.MONGO_URI)
            self.db = self.client[settings.MONGO_DB_NAME]
            
            # Collection lưu lịch sử chat (cho UI)
            self.history_col: Collection = self.db["conversations"]
            
            # Collection lưu state của Agent (LangGraph Checkpointer writes here)
            # Lưu ý: Tên collection này cần khớp với config lúc compile Graph
            self.checkpoint_col: Collection = self.db["checkpoints"]
            
            # Ping để kiểm tra kết nối
            self.client.admin.command('ping')
            logger.info(f"✅ MongoHistory connected to {settings.MONGO_DB_NAME}")
            
        except errors.ConnectionFailure as e:
            logger.critical(f"❌ Failed to connect to MongoDB: {str(e)}")
            raise e

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history for a session.
        Returns a list of message dicts: [{'role': 'user', 'content': '...'}, ...]
        """
        try:
            doc = self.history_col.find_one({"session_id": session_id})
            if doc and "messages" in doc:
                return doc["messages"]
            return []
        except Exception as e:
            logger.error(f"Error retrieving history for {session_id}: {str(e)}")
            return []

    def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """
        Append a new message to the session.
        Upsert: Creates document if not exists.
        """
        try:
            self.history_col.update_one(
                {"session_id": session_id},
                {"$push": {"messages": message}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error adding message to {session_id}: {str(e)}")
            # Không raise để tránh gián đoạn luồng chat chính

    def clear_history(self, session_id: str) -> None:
        """
        Delete session history.
        """
        try:
            self.history_col.delete_one({"session_id": session_id})
            logger.info(f"Cleared history for session: {session_id}")
        except Exception as e:
            logger.error(f"Error clearing history for {session_id}: {str(e)}")

    def get_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the latest checkpoint state for a thread.
        This reads raw data written by LangGraph's MongoDBSaver.
        """
        try:
            # LangGraph thường lưu checkpoint với thread_id làm key (hoặc trong metadata)
            # Query này phụ thuộc vào schema của MongoDBSaver
            # Giả định schema: {_id: thread_id, checkpoint: {...}} hoặc tìm theo field thread_id
            
            # Cách 1: Tìm document mới nhất của thread_id (nếu lưu dạng log)
            doc = self.checkpoint_col.find_one(
                {"thread_id": thread_id},
                sort=[("ts", -1)] # Sort theo timestamp giảm dần
            )
            
            if doc:
                # Trả về phần checkpoint chứa state
                return doc.get("checkpoint")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving checkpoint for {thread_id}: {str(e)}")
            return None