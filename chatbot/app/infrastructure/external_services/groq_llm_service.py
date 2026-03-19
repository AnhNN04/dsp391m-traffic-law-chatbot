"""
Groq LLM Service Implementation

Concrete implementation of ILLMService using Groq's inference API.
Used for fast, lightweight tasks (routing, guardrails, quick classification).

Author: AnhNN217-FHN
"""

from typing import Type, TypeVar, List, Dict, Optional, Any
from pydantic import BaseModel

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser

from app.domain.interfaces.i_llm_service import ILLMService
from app.domain.exceptions import LLMConnectionError, LLMOutputError, LLMRateLimitError
from app.infrastructure.config import get_logger, settings

logger = get_logger(__name__)

T = TypeVar('T', bound=BaseModel)

class GroqLLMService(ILLMService):
    """
    Groq LLama-3 implementation of ILLMService.
    
    This service uses Groq's ultra-fast inference for quick tasks.
    Suitable for:
    - Guardrails (safety checks)
    - Intent routing (classification)
    - Quick yes/no decisions
    
    Groq provides free tier with fast inference (< 500ms typical).
    
    Attributes:
        client: LangChain ChatGroq instance
        model: Model name (e.g., "llama-3.1-8b-instant")
        temperature: Default temperature for generation
    
    Example:
        >>> service = GroqLLMService(
        ...     api_key="gsk_...",
        ...     model="llama-3.1-8b-instant"
        ... )
        >>> response = service.generate("Is this safe: Hello")
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.1-8b-instant",
        temperature: float = 0.1,
        max_retries: int = 2,
        timeout: int = 20
    ):
        """
        Initialize Groq service.
        
        Args:
            api_key: Groq API key (starts with gsk_)
            model: Model name (default: llama-3.1-8b-instant)
            temperature: Sampling temperature (default: 0.1 for consistency)
            max_retries: Number of retries on failure
            timeout: Request timeout in seconds
        """
        self.model = model
        self.temperature = temperature
        
        try:
            self.client = ChatGroq(
                groq_api_key=api_key,
                model_name=model,
                temperature=temperature,
                max_retries=max_retries,
                timeout=timeout
            )
            logger.info(
                "Groq service initialized",
                model=model,
                temperature=temperature
            )
        except Exception as e:
            logger.error(
                "Failed to initialize Groq service",
                error=str(e),
                model=model
            )
            raise LLMConnectionError(
                "Failed to initialize Groq service",
                provider="Groq",
                model=model
            ) from e
    
    def generate(self, prompt: str, system_message: str = None, temperature: float = 0.1, max_tokens: int = None, stop_sequences: list = None) -> str:
        """
        Generate text response from a prompt.
        
        Args:
            prompt: The user prompt/query
        
        Returns:
            Generated text response
        
        Raises:
            LLMConnectionError: If API call fails
            LLMRateLimitError: If rate limit exceeded
            LLMOutputError: If output is invalid or empty
        
        Example:
            >>> response = service.generate(
            ...     "Is this input safe: Vượt đèn đỏ phạt bao nhiêu?"
            ... )
            >>> print(response)  # "SAFE"
        """
        try:
            logger.debug(
                "Generating text with Groq",
                model=self.model,
                prompt_length=len(prompt)
            )
            
            # Build messages with optional system message
            from langchain_core.messages import SystemMessage
            messages = []
            if system_message:
                messages.append(SystemMessage(content=system_message))
            messages.append(HumanMessage(content=prompt))
            
            # Invoke LLM
            response = self.client.invoke(messages)
            
            # Extract content
            result = response.content.strip()
            
            if not result:
                raise LLMOutputError(
                    "Groq returned empty response",
                    output=result,
                    expected_format="non-empty text"
                )
            
            logger.debug(
                "Groq generation successful",
                output_length=len(result)
            )
            
            return result
            
        except LLMOutputError:
            # Re-raise our custom exceptions
            raise
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for rate limit errors
            if "rate limit" in error_msg or "429" in error_msg:
                logger.warning(
                    "Groq rate limit exceeded",
                    error=str(e),
                    model=self.model
                )
                raise LLMRateLimitError(
                    "Groq rate limit exceeded",
                    provider="Groq",
                    retry_after=60  # Typical Groq cooldown
                ) from e
            
            logger.error(
                "Groq API call failed",
                error=str(e),
                error_type=type(e).__name__,
                prompt=prompt[:100]
            )
            raise LLMConnectionError(
                f"Groq API call failed: {str(e)}",
                provider="Groq",
                model=self.model
            ) from e

    def generate_text(self, prompt: str, system_message: str = None, **kwargs) -> str:
        """Alias for generate() — used by application nodes."""
        return self.generate(prompt, system_message=system_message)

    def generate_structured(self, prompt: str, schema: Type[T]) -> T:
        """
        Generate structured output conforming to a Pydantic schema.
        
        Note: Groq/LLama-3 may not support native structured output
        as well as GPT-4. We use JSON mode + parsing as a fallback.
        
        Args:
            prompt: The user prompt/query
            schema: Pydantic model class defining expected output structure
        
        Returns:
            Instance of the schema class with parsed LLM output
        
        Raises:
            LLMConnectionError: If API call fails
            LLMOutputError: If output doesn't match schema
        
        Example:
            >>> from pydantic import BaseModel
            >>> 
            >>> class SafetyCheck(BaseModel):
            ...     is_safe: bool
            ...     reason: str
            >>> 
            >>> result = service.generate_structured(
            ...     "Check safety: Hello world",
            ...     schema=SafetyCheck
            ... )
            >>> print(result.is_safe)  # True
        """
        try:
            logger.debug(
                "Generating structured output with Groq",
                model=self.model,
                schema=schema.__name__,
                prompt_length=len(prompt)
            )
            
            # Create parser
            parser = PydanticOutputParser(pydantic_object=schema)
            
            # Add format instructions to prompt
            format_instructions = parser.get_format_instructions()
            enhanced_prompt = f"{prompt}\n\n{format_instructions}"
            
            # Create message
            message = HumanMessage(content=enhanced_prompt)
            
            # Invoke LLM
            response = self.client.invoke([message])
            
            # Parse output
            try:
                result = parser.parse(response.content)
            except Exception as parse_error:
                logger.error(
                    "Failed to parse Groq output",
                    error=str(parse_error),
                    output=response.content[:200],
                    schema=schema.__name__
                )
                raise LLMOutputError(
                    f"Failed to parse Groq output: {str(parse_error)}",
                    output=response.content,
                    expected_format=schema.__name__
                ) from parse_error
            
            logger.debug(
                "Groq structured generation successful",
                schema=schema.__name__,
                result=str(result)[:100]
            )
            
            return result
            
        except (LLMOutputError, LLMRateLimitError):
            # Re-raise our custom exceptions
            raise
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for rate limit
            if "rate limit" in error_msg or "429" in error_msg:
                raise LLMRateLimitError(
                    "Groq rate limit exceeded",
                    provider="Groq",
                    retry_after=60
                ) from e
            
            logger.error(
                "Groq structured generation failed",
                error=str(e),
                error_type=type(e).__name__,
                schema=schema.__name__,
                prompt=prompt[:100]
            )
            raise LLMOutputError(
                f"Failed to generate structured output: {str(e)}",
                output=None,
                expected_format=schema.__name__
            ) from e

    def generate_with_tools(self, prompt: str, tools: List[Dict[str, Any]], system_message: Optional[str] = None, temperature: float = 0.1) -> Dict[str, Any]:
        """
        Generate response with tool/function calling capability.

        Args:
            prompt: The user prompt/query
            tools: List of tool definitions in OpenAI function calling format
            system_message: Optional system instruction
            temperature: Sampling temperature

        Returns:
            Dictionary with 'content' (text) and 'tool_calls' (if any)

        Raises:
            NotImplementedError: If the method is not implemented
        """
        raise NotImplementedError("generate_with_tools is not implemented yet.")

    def generate_streaming(self, prompt: str, system_message: Optional[str] = None, temperature: float = 0.1):
        """
        Generate text with streaming response (yields tokens as they arrive).

        Args:
            prompt: The user prompt/query
            system_message: Optional system instruction
            temperature: Sampling temperature

        Yields:
            Text chunks as they are generated

        Raises:
            NotImplementedError: If the method is not implemented
        """
        raise NotImplementedError("generate_streaming is not implemented yet.")

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens

        Example:
            >>> token_count = service.count_tokens("Vượt đèn đỏ phạt bao nhiêu?")
            >>> print(f"Query uses {token_count} tokens")
        """
        # Placeholder implementation, replace with actual token counting logic
        return len(text.split())

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model being used.

        Returns:
            Dictionary with model name, provider, context window, etc.

        Example:
            >>> info = service.get_model_info()
            >>> print(f"Using {info['model']} from {info['provider']}")
            >>> print(f"Context window: {info['context_window']} tokens")
        """
        return {
            "model": self.model,
            "provider": "Groq",
            "temperature": self.temperature,
            "context_window": 4096  # Example value, replace with actual
        }

    def validate_api_key(self) -> bool:
        """
        Validate that the API key is working.

        Makes a minimal API call to verify authentication.

        Returns:
            True if API key is valid, False otherwise

        Example:
            >>> if not service.validate_api_key():
            ...     raise ConfigurationError("Invalid LLM API key")
        """
        try:
            # Perform a minimal API call to validate the key
            self.client.invoke([HumanMessage(content="ping")])
            return True
        except Exception as e:
            logger.error("API key validation failed", error=str(e))
            return False

    @classmethod
    def from_settings(cls) -> "GroqLLMService":
        """
        Create Groq service from application settings.
        
        Returns:
            Configured GroqLLMService instance
        
        Example:
            >>> service = GroqLLMService.from_settings()
        """
        return cls(
            api_key=settings.GROQ_API_KEY,
            model=settings.FAST_LLM_MODEL,
            temperature=settings.DEFAULT_TEMPERATURE
        )
