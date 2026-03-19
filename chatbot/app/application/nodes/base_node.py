"""
Base Node Class for LangGraph Agent Nodes.

Cung cấp interface chung và các tiện ích cho tất cả các Node trong hệ thống.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from app.domain.state import AgentState
from app.infrastructure.config.logger import get_logger

logger = get_logger(__name__)


class BaseNode(ABC):
    """
    Abstract Base Class cho tất cả các Node trong LangGraph.
    
    Mỗi Node phải implement method __call__ để xử lý logic nghiệp vụ.
    """
    
    def __init__(self, node_name: str):
        """
        Initialize base node.
        
        Args:
            node_name: Tên của node (dùng cho logging)
        """
        self.node_name = node_name
    
    @abstractmethod
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Xử lý logic nghiệp vụ của Node.
        
        Args:
            state: Trạng thái hiện tại của Graph
            
        Returns:
            Dict chứa các field cần update vào state
        """
        pass
    
    def _log_entry(self, state: AgentState) -> None:
        """Log khi bắt đầu xử lý Node."""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        logger.info(
            f"[{self.node_name}] 🎯 Starting | Last message: {last_message.content[:50] if last_message else 'None'}..."
        )
    
    def _log_exit(self, result: Dict[str, Any]) -> None:
        """Log khi kết thúc xử lý Node."""
        logger.info(
            f"[{self.node_name}] ✅ Completed | Updates: {list(result.keys())}"
        )
    
    def _log_error(self, error: Exception) -> None:
        """Log khi có lỗi."""
        logger.error(
            f"[{self.node_name}] ❌ Error: {str(error)}",
            exc_info=True
        )
    
    def _validate_state(self, state: AgentState, required_keys: list[str]) -> None:
        """
        Validate state có đủ các field bắt buộc.
        
        Args:
            state: State cần validate
            required_keys: List các key bắt buộc phải có
            
        Raises:
            ValueError: Nếu thiếu required key
        """
        missing_keys = [key for key in required_keys if key not in state]
        if missing_keys:
            raise ValueError(
                f"[{self.node_name}] State thiếu các field: {missing_keys}"
            )
