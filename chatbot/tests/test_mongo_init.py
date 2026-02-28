"""
MongoDB Initialization & Health Check Module

Responsibilities:
- Connect to MongoDB (local for development stage)
- Test connectivity (ping)
- Verify read/write permissions
- Ensure required collections exist
- Ensure indexes are created (idempotent & background)
- Log clearly via centralized logger
"""

from pymongo import MongoClient, ASCENDING
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.infrastructure.config.settings import settings
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)


def init_mongodb() -> Database:
    """
    Initialize and verify MongoDB connection.

    Returns:
        Database: MongoDB database instance
    """
    logger.info("Starting MongoDB initialization")

    try:
        # ----------------------------
        # Connect
        # ----------------------------
        # log uri for checking:
        
        logger.debug(
            f"Connecting to MongoDB at {settings.MONGO_URI} (DB: {settings.MONGO_DB_NAME})"
        )

        # Khởi tạo client với timeout rõ ràng để không treo app nếu Docker chưa lên
        client = MongoClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000, # 5 giây
            retryWrites=True,
            appname="traffic-law-bot",
        )

        # ----------------------------
        # Ping
        # ----------------------------
        logger.info("Pinging MongoDB server...")
        client.admin.command("ping")
        logger.info("MongoDB connection successful!") # Đổi thành .info thay vì .success để tương thích standard logging

        # ----------------------------
        # Select database
        # ----------------------------
        db = client[settings.MONGO_DB_NAME]
        logger.info(f"Database selected: {settings.MONGO_DB_NAME}")

        # ----------------------------
        # Verify write permission
        # ----------------------------
        _verify_write_permission(db)

        # ----------------------------
        # Ensure collections
        # ----------------------------
        _ensure_collections(db)

        # ----------------------------
        # Ensure indexes
        # ----------------------------
        _ensure_indexes(db)

        logger.info("MongoDB initialization completed successfully.")
        return db

    except PyMongoError as e:
        logger.critical(
            f"MongoDB initialization failed! Error: {str(e)} (Type: {type(e).__name__})"
        )
        raise


def _verify_write_permission(db: Database) -> None:
    """Verify that the application has write permission."""
    logger.info("Verifying write permissions...")

    test_collection = db["_healthcheck"]
    
    # Thử Insert và sau đó Delete ngay lập tức
    result = test_collection.insert_one({"status": "ok"})
    test_collection.delete_one({"_id": result.inserted_id})

    logger.info("Write permission verified successfully.")


def _ensure_collections(db: Database) -> None:
    """Ensure required collections exist."""
    logger.info("Ensuring MongoDB collections...")

    existing = set(db.list_collection_names())

    required = {
        settings.MONGO_COLLECTION,
        "user_sessions",
    }

    for name in required:
        if name not in existing:
            db.create_collection(name)
            logger.info(f"Collection created: {name}")
        else:
            logger.debug(f"Collection already exists: {name}")


def _ensure_indexes(db: Database) -> None:
    """Ensure required indexes exist (idempotent)."""
    logger.info("Ensuring MongoDB indexes...")

    chat_collection = db[settings.MONGO_COLLECTION]
    session_collection = db["user_sessions"]

    # ---- Chat history indexes ----
    # Thêm background=True để không block DB khi build index
    chat_collection.create_index(
        [("thread_id", ASCENDING)],
        name="idx_thread_id",
        background=True 
    )

    chat_collection.create_index(
        [("created_at", ASCENDING)],
        name="idx_created_at",
        background=True
    )

    # ---- User session indexes ----
    session_collection.create_index(
        [("user_id", ASCENDING)],
        name="idx_user_id",
        background=True
    )

    logger.info("Indexes ensured successfully.")


# ----------------------------------------------------------
# Standalone execution (For manual testing)
# ----------------------------------------------------------
if __name__ == "__main__":
    # Đảm bảo bạn đã import/setup logger đúng cách trước khi chạy file này độc lập
    # from app.infrastructure.config.logger import setup_logger
    # setup_logger(log_level=settings.LOG_LEVEL)
    
    init_mongodb()
