"""
Chat History Interface

Abstract interface for conversation persistence operations.
Concrete implementations: MongoDB, Redis, Postgres.

Author: AnhNN217-FHN
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class IChatHistory(ABC):
    """
    Abstract interface for managing conversation history persistence.
    
    This interface defines the contract for storing and retrieving chat sessions.
    The implementation is crucial for the 'State Management' layer of the Agent,
    allowing the bot to remember context across multiple turns.
    
    """

    @abstractmethod
    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve the full conversation history for a specific session.
        
        Args:
            session_id: The unique identifier for the user session.
            
        Returns:
            List of message dictionaries (e.g., [{'role': 'user', 'content': '...'}, ...]).
            Returns an empty list if the session does not exist.
            
        Raises:
            DatabaseConnectionError: If DB is unreachable.
        
        Example:
            >>> history = chat_repo.get_history("session_123")
            >>> print(f"Last message: {history[-1]['content']}")
        """
        pass

    @abstractmethod
    def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """
        Append a new message to the conversation history.
        
        This method should handle creating a new session document if one
        does not already exist.
        
        Args:
            session_id: The unique identifier for the user session.
            message: The message object to store (usually LangChain message format).
            
        """
        pass

    @abstractmethod
    def clear_history(self, session_id: str) -> None:
        """
        Delete the conversation history for a specific session.
        
        Useful for 'Reset Chat' features or complying with data privacy requests.
        
        Args:
            session_id: The unique identifier to delete.
            
        """
        pass
        
    @abstractmethod
    def get_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the latest LangGraph checkpoint state.
        
        Used specifically for recovering complex Agent State (variables, flags)
        beyond just the raw message list.
        
        Args:
            thread_id: The unique thread ID used by LangGraph.
            
        Returns:
            The serialized checkpoint dict or None.
        """
        pass
