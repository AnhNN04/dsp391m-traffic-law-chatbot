"""
ILLMService Interface

This module defines the ILLMService interface, which specifies the contract for
interacting with Large Language Models (LLMs). It includes methods for generating
free-form text, structured outputs, and other utilities like token counting and
streaming responses.

Typical implementations include OpenAI, Groq, and other LLM providers.

Author: AnhNN217-FHN
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class ILLMService(ABC):
    """
    Abstract interface for LLM operations.
    
    Defines the contract for LLM service implementations.
    It supports both free-form text generation and structured output generation.
    
    Different LLMs can be used for different purposes:
    - Smart LLM (GPT-4o-mini): Complex reasoning, query rewriting, answer generation
    - Fast LLM (Llama-3 via Groq): Quick tasks like routing, guardrails
    
    """
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None
    ) -> str:
        """
        Generate text response from a prompt.
        
        Free-form LLM output.
        
        Args:
            prompt: The user prompt/query
            system_message: Optional system instruction to guide the LLM
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum number of tokens to generate
            stop_sequences: List of sequences that stop generation
        
        Returns:
            Generated text response
        
        Raises:
            LLMConnectionError: If API call fails
            LLMOutputError: If output is invalid or empty
        
        Example:
            >>> llm = OpenAIService(api_key="sk-...", model="gpt-4o-mini")
            >>> response = llm.generate(
            ...     prompt="Viết lại câu hỏi: Nó phạt bao nhiêu?",
            ...     system_message="You are a helpful assistant",
            ...     temperature=0.0
            ... )
            >>> print(response)
            "Lỗi vượt đèn đỏ với xe máy phạt bao nhiêu?"
        """
        pass
    
    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_message: Optional[str] = None,
        temperature: float = 0.1
    ) -> T:
        """
        Generate structured output conforming to a Pydantic schema.
        
        This method ensures the LLM output matches a specific structure,
        which is crucial for routing, classification, and data extraction.
        
        Args:
            prompt: The user prompt/query
            schema: Pydantic model class defining the expected output structure
            system_message: Optional system instruction
            temperature: Sampling temperature
        
        Returns:
            Instance of the schema class with parsed LLM output
        
        Raises:
            LLMConnectionError: If API call fails
            LLMOutputError: If output doesn't match schema
        
        Example:
            >>> from pydantic import BaseModel
            >>> 
            >>> class IntentClassification(BaseModel):
            ...     intent: str
            ...     confidence: float
            >>> 
            >>> result = llm.generate_structured(
            ...     prompt="Vượt đèn đỏ phạt bao nhiêu?",
            ...     schema=IntentClassification,
            ...     system_message="Classify the intent"
            ... )
            >>> print(result.intent)  # "legal"
            >>> print(result.confidence)  # 0.95
        """
        pass
    
    @abstractmethod
    def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_message: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Generate response with tool/function calling capability.
        
        This enables the LLM to decide when to call external tools
        during the generation process (agent-like behavior).
        
        Args:
            prompt: The user prompt/query
            tools: List of tool definitions in OpenAI function calling format
            system_message: Optional system instruction
            temperature: Sampling temperature
        
        Returns:
            Dictionary with 'content' (text) and 'tool_calls' (if any)
        
        Example:
            >>> tools = [{
            ...     "name": "search_law",
            ...     "description": "Search legal database",
            ...     "parameters": {"query": {"type": "string"}}
            ... }]
            >>> 
            >>> result = llm.generate_with_tools(
            ...     prompt="Tìm luật về vượt đèn đỏ",
            ...     tools=tools
            ... )
            >>> if result.get("tool_calls"):
            ...     # LLM decided to call search_law tool
            ...     pass
        """
        pass
    
    @abstractmethod
    def generate_streaming(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.1
    ):
        """
        Generate text with streaming response (yields tokens as they arrive).
        
        Useful for real-time chat interfaces where you want to show
        the response as it's being generated.
        
        Args:
            prompt: The user prompt/query
            system_message: Optional system instruction
            temperature: Sampling temperature
        
        Yields:
            Text chunks as they are generated
        
        Example:
            >>> for chunk in llm.generate_streaming("Explain traffic law"):
            ...     print(chunk, end="", flush=True)
        """
        pass
    
    @abstractmethod
    def count_tokens(
        self,
        text: str
    ) -> int:
        """
        Count the number of tokens in a text.
        
        Useful for managing context windows and estimating costs.
        
        Args:
            text: Text to count tokens for
        
        Returns:
            Number of tokens
        
        Example:
            >>> token_count = llm.count_tokens("Vượt đèn đỏ phạt bao nhiêu?")
            >>> print(f"Query uses {token_count} tokens")
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model being used.
        
        Returns:
            Dictionary with model name, provider, context window, etc.
        
        Example:
            >>> info = llm.get_model_info()
            >>> print(f"Using {info['model']} from {info['provider']}")
            >>> print(f"Context window: {info['context_window']} tokens")
        """
        pass
    
    @abstractmethod
    def validate_api_key(self) -> bool:
        """
        Validate that the API key is working.
        
        Makes a minimal API call to verify authentication.
        
        Returns:
            True if API key is valid, False otherwise
        
        Example:
            >>> if not llm.validate_api_key():
            ...     raise ConfigurationError("Invalid LLM API key")
        """
        pass
