"""
Configuration Management Module

This module handles all application settings using Pydantic Settings.
Environment variables are loaded from .env file and validated at startup.

Usage:
    from app.infrastructure.config.settings import settings
        
Author: AnhNN217-FHN
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    
    Priority:
    1. Environment variables
    2. .env file (if exists)
    3. Default values (if specified)
    """
    
    # ==================== APPLICATION CONFIG ====================
    APP_ENV: str = Field(
        default="development", 
        description="Environment: development, production, test"
        )
    LOG_LEVEL: str = Field(
        default="INFO", 
        description="Logging level"
        )
    
    
    # ==================== LLM PROVIDERS API ====================
    # Smart Node (Rewrite, Generate)
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key (optional, not used when Groq is used for all nodes)")
    GOOGLE_API_KEY: Optional[str] = Field(
        default=None, 
        description="Google AI API key for embeddings"
        )

    # Fast Node (Guardrails, Router, Classification)
    GROQ_API_KEY: str = Field(..., description="Groq API key (required)")

    # Web Search Node
    TAVILY_API_KEY: Optional[str] = Field(
        default=None, 
        description="Tavily Search API key"
        )
    
    # ==================== LLM Model Names ====================
    SMART_LLM_MODEL: str = Field(
        default="gpt-4o-mini", 
        description="OpenAI model name"
        )
    FAST_LLM_MODEL: str = Field(
        default="openai/gpt-oss-120b", 
        description="Groq model name"
        )
    EMBEDDING_MODEL: str = Field(
        default="intfloat/multilingual-e5-small", 
        description="Embedding model for vector store"
        )
    EMBEDDING_DIMENSIONS: int = Field(
        default=384, 
        description="Dimensions of the embedding model"
        )
    
    # ==================== DATABASES CONNECTIONS ====================
    # MongoDB (State persistence)
    MONGO_URI: str = Field(
        default="mongodb://admin:password123@localhost:27017", 
        description="MongoDB connection URI"
        )
    MONGO_DB_NAME: str = Field(
        default="traffic_law_db", 
        description="MongoDB database name"
        )
    MONGO_COLLECTION: str = Field(
        default="chat_history", 
        description="MongoDB collection name for agent state"
        )
    
    # ChromaDB PATHS (Vector store)
    CHROMA_PERSIST_DIR: str = Field(
        default="./data/chroma_db", 
        description="ChromaDB persistence directory"
        )
    CHROMA_COLLECTION_NAME: str = Field(
        default="traffic_law", 
        description="ChromaDB collection name"
        )
    
    # Neo4j (Graph store - Optional)
    NEO4J_URI: Optional[str] = Field(
        default=None, 
        description="Neo4j connection URI (bolt://...)"
        )
    NEO4J_USERNAME: Optional[str] = Field(
        default="neo4j", 
        description="Neo4j username"
        )
    NEO4J_PASSWORD: Optional[str] = Field(
        default=None, 
        description="Neo4j password"
        )
    
    # ==================== Feature Flags ====================
    ENABLE_NEO4J: bool = Field(
        default=False, 
        description="Enable Neo4j graph store"
        )
    ENABLE_WEB_SEARCH: bool = Field(
        default=True, 
        description="Enable web search fallback"
        )
    
    # ==================== Performance Tuning ====================
    MAX_RETRIEVAL_DOCS: int = Field(
        default=10, 
        description="Max documents to retrieve from vector store"
        )
    MAX_WEB_SEARCH_RESULTS: int = Field(
        default=3, 
        description="Max web search results"
        )
    REWRITE_HISTORY_WINDOW: int = Field(
        default=5, 
        description="Number of previous messages to include in rewrite context"
        )
    DEFAULT_TEMPERATURE: float = Field(
        default=0.1, 
        description="LLM temperature (0=deterministic, 1=creative)"
        )
    DEFAULT_TIMEOUT: int = Field(
        default=30, 
        description="LLM request timeout in seconds"
        )
    
    # ==================== Pydantic Config ====================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra env vars
    )
    
    # ==================== field_validators ====================
    @field_validator("APP_ENV", mode="before")
    def validate_env(cls, v):
        """Validate APP_ENV is one of allowed values."""
        allowed = ["development", "production", "test"]
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}, got '{v}'")
        return v

    @field_validator("LOG_LEVEL", mode="before")
    def validate_log_level(cls, v):
        """Validate LOG_LEVEL is valid."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got '{v}'")
        return v_upper

    @field_validator("DEFAULT_TEMPERATURE", mode="before")
    def validate_temperature(cls, v):
        """Validate temperature is in valid range."""
        try:
            v = float(v)  # Chuyển đổi giá trị sang float
        except ValueError:
            raise ValueError(f"DEFAULT_TEMPERATURE must be a float, got '{v}'")

        if not 0.0 <= v <= 2.0:
            raise ValueError(f"DEFAULT_TEMPERATURE must be between 0.0 and 2.0, got {v}")
        return v

    # ==================== Helper Methods ====================
    def has_neo4j(self) -> bool:
        """True nếu Neo4j được cấu hình (có URI và password)."""
        return bool(self.ENABLE_NEO4J and self.NEO4J_URI and self.NEO4J_PASSWORD)

    def has_web_search(self) -> bool:
        """True nếu Tavily web search được cấu hình."""
        return bool(self.ENABLE_WEB_SEARCH and self.TAVILY_API_KEY)


# ==================== Singleton Instance ====================
# Create a singleton instance to be imported throughout the app
# Usage: from app.shared.config import settings
try:
    settings = Settings()
except Exception as e:
    print(f"Failed to load settings: {e}")
    print("Please check your .env file and environment variables.")
    raise
