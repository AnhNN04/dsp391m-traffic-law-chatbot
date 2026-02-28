"""
Dependency Injection Container (Composition Root).

Nhiệm vụ:
- Là NƠI DUY NHẤT khởi tạo các object cụ thể (Concrete Classes).
- Quản lý Lifecycle của tất cả dependencies thông qua mẫu Lazy Loading.
- Wire (kết nối) các Application Nodes với các Infrastructure Services.

Nguyên tắc:
- Application Layer (Nodes, Workflows) không được phép biết về sự tồn tại của file này.
- Sử dụng Local Imports để tránh Circular Dependencies.
"""

from typing import Optional, Any, TYPE_CHECKING
from langgraph.checkpoint.memory import MemorySaver

from app.infrastructure.config import settings
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)

# Sử dụng TYPE_CHECKING để hỗ trợ IDE Autocomplete mà không gây lỗi import chéo khi runtime
if TYPE_CHECKING:
    from app.infrastructure.external_services.openai_service import OpenAIService
    from app.infrastructure.external_services.groq_service_impl import ConcreteGroqService
    from app.infrastructure.external_services.tavily_service import TavilyService
    from app.infrastructure.persistence.chroma_repo import ChromaRepo
    from app.infrastructure.persistence.neo4j_repo import Neo4jRepo
    from app.application.nodes import (
        GuardrailsNode, RewriteNode, RouterNode, RetrievalNode,
        GradeNode, AskHumanNode, WebSearchNode, GenerateNode
    )

class Container:
    """
    Container quản lý toàn bộ hệ thống Traffic Law Agent.
    """

    def __init__(self):
        """
        Khởi tạo Container ở trạng thái chờ (Lazy).
        Chỉ load Settings và Logger vì đây là các thành phần cơ bản nhất.
        """
        logger.info("=" * 60)
        logger.info("🚀 INITIALIZING TRAFFIC LAW AGENT CONTAINER")
        logger.info(f"📋 Environment: {settings.APP_ENV}")
        logger.info("=" * 60)
        
        self.settings = settings

        # --- Infrastructure Cache ---
        self._openai_service: Optional[Any] = None
        self._groq_service: Optional[Any] = None
        self._chroma_repo: Optional[Any] = None
        self._neo4j_repo: Optional[Any] = None
        self._tavily_service: Optional[Any] = None
        
        # --- Application Nodes Cache ---
        self._guardrails_node: Optional[Any] = None
        self._rewrite_node: Optional[Any] = None
        self._router_node: Optional[Any] = None
        self._retrieval_node: Optional[Any] = None
        self._grade_node: Optional[Any] = None
        self._ask_human_node: Optional[Any] = None
        self._web_search_node: Optional[Any] = None
        self._generate_node: Optional[Any] = None
        
        # --- Workflow Cache ---
        self._graph: Optional[Any] = None

    # ==================== 1. Infrastructure Services ====================

    @property
    def openai_service(self) -> "OpenAIService":
        """Khởi tạo OpenAI Service (Smart LLM) - Dùng cho các tác vụ cần suy luận cao."""
        if self._openai_service is None:
            logger.info("🔧 Initializing OpenAI service...")
            from app.infrastructure.external_services.openai_service import OpenAIService
            self._openai_service = OpenAIService(
                api_key=self.settings.OPENAI_API_KEY,
                model=self.settings.SMART_LLM_MODEL,
                temperature=self.settings.DEFAULT_TEMPERATURE
            )
            logger.info(f"✅ OpenAI Service ready (Model: {self.settings.SMART_LLM_MODEL})")
        return self._openai_service

    @property
    def groq_service(self) -> "GroqService":
        """Khởi tạo Groq Service (Fast LLM) - Dùng cho Guardrails hoặc các tác vụ nhanh."""
        if self._groq_service is None:
            from app.infrastructure.external_services.groq_service import ConcreteGroqService
            self._groq_service = ConcreteGroqService(
                api_key=self.settings.GROQ_API_KEY,
                model=self.settings.FAST_LLM_MODEL
            )
        return self._groq_service

    @property
    def chroma_repo(self) -> "ChromaRepo":
        """Khởi tạo Vector Store (ChromaDB)."""
        if self._chroma_repo is None:
            logger.info("🔧 Initializing ChromaDB repository...")
            from app.infrastructure.persistence.chroma_repo import ChromaRepo
            self._chroma_repo = ChromaRepo(
                persist_directory=self.settings.CHROMA_PERSIST_DIR,
                collection_name=self.settings.CHROMA_COLLECTION_NAME
            )
            logger.info("✅ ChromaDB ready.")
        return self._chroma_repo

    @property
    def neo4j_repo(self) -> Optional["Neo4jRepo"]:
        """Khởi tạo Graph Store (Neo4j) - Thành phần tùy chọn."""
        if self._neo4j_repo is None and self.settings.has_neo4j():
            logger.info("🔧 Initializing Neo4j repository...")
            try:
                from app.infrastructure.persistence.neo4j_repo import Neo4jRepo
                self._neo4j_repo = Neo4jRepo(
                    uri=self.settings.NEO4J_URI,
                    username=self.settings.NEO4J_USERNAME,
                    password=self.settings.NEO4J_PASSWORD
                )
                logger.info("✅ Neo4j ready.")
            except Exception as e:
                logger.warning(f"⚠️ Neo4j failed to start: {e}. System will fallback to Vector-only.")
                self._neo4j_repo = None
        return self._neo4j_repo

    @property
    def tavily_service(self) -> Optional["TavilyService"]:
        """Khởi tạo Web Search Service (Tavily)."""
        if self._tavily_service is None and self.settings.has_web_search():
            logger.info("🔧 Initializing Tavily search service...")
            from app.infrastructure.external_services.tavily_service import TavilyService
            self._tavily_service = TavilyService(api_key=self.settings.TAVILY_API_KEY)
            logger.info("✅ Tavily search ready.")
        return self._tavily_service

    # ==================== 2. Application Nodes (Wiring) ====================

    @property
    def guardrails_node(self) -> "GuardrailsNode":
        if self._guardrails_node is None:
            from app.application.nodes.guardrails_node import GuardrailsNode
            self._guardrails_node = GuardrailsNode(fast_llm=self.groq_service)
        return self._guardrails_node

    @property
    def rewrite_node(self) -> "RewriteNode":
        if self._rewrite_node is None:
            from app.application.nodes.rewrite_node import RewriteNode
            self._rewrite_node = RewriteNode()
        return self._rewrite_node

    @property
    def router_node(self) -> "RouterNode":
        if self._router_node is None:
            from app.application.nodes.router_node import RouterNode
            self._router_node = RouterNode()
        return self._router_node

    @property
    def retrieval_node(self) -> "RetrievalNode":
        if self._retrieval_node is None:
            from app.application.nodes.retrieval_node import RetrievalNode
            self._retrieval_node = RetrievalNode()
        return self._retrieval_node

    @property
    def grade_node(self) -> "GradeNode":
        if self._grade_node is None:
            from app.application.nodes.grade_node import GradeNode
            self._grade_node = GradeNode()
        return self._grade_node

    @property
    def ask_human_node(self) -> "AskHumanNode":
        if self._ask_human_node is None:
            from app.application.nodes.ask_human_node import AskHumanNode
            self._ask_human_node = AskHumanNode()
        return self._ask_human_node

    @property
    def web_search_node(self) -> "WebSearchNode":
        if self._web_search_node is None:
            from app.application.nodes.web_search_node import WebSearchNode
            self._web_search_node = WebSearchNode()
        return self._web_search_node

    @property
    def generate_node(self) -> "GenerateNode":
        if self._generate_node is None:
            from app.application.nodes.generate_node import GenerateNode
            self._generate_node = GenerateNode()
        return self._generate_node

    @property
    def mongo_history(self):
        """Khởi tạo MongoDB client."""
        if not hasattr(self, "_mongo_history"):
            from app.infrastructure.persistence.mongo_history import MongoHistory
            self._mongo_history = MongoHistory(
                uri=self.settings.MONGO_URI,
                db_name=self.settings.MONGO_DB_NAME,
                collection=self.settings.MONGO_COLLECTION
            )
        return self._mongo_history

    # ==================== 3. LangGraph Workflow ====================

    @property
    def graph(self):
        """Build và Compile LangGraph Workflow."""
        if self._graph is None:
            from app.application.workflows.main_graph import build_traffic_law_graph
            self._graph = build_traffic_law_graph()
        return self._graph

    # ==================== 4. Lifecycle Management ====================

    def cleanup(self):
        """Dọn dẹp tài nguyên (đóng connection) khi ứng dụng tắt."""
        logger.info("🧹 Container cleanup in progress...")
        if self._neo4j_repo is not None:
            try:
                self._neo4j_repo.close()
                logger.info("✅ Neo4j connection closed.")
            except Exception as e:
                logger.error(f"❌ Error closing Neo4j: {e}")
        logger.info("✅ Cleanup completed.")


# --- Khởi tạo Singleton Instance ---
# Điều này đảm bảo toàn bộ ứng dụng dùng chung một Container duy nhất.
container = Container()

# Chỉ export instance này để sử dụng ở các file khác (ví dụ: main.py)
__all__ = ["container"]
