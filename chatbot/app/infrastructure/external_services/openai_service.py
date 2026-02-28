"""
OpenAI Service Implementation

Concrete implementation of ILLMService using OpenAI's GPT models.
Used for complex reasoning tasks (query rewriting, answer generation).

Author: AnhNN217-FHN
"""

from typing import Type, TypeVar
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.application.interfaces import ILLMService
from app.domain.exceptions import LLMConnectionError, LLMOutputError
from app.infrastructure.config import get_logger, settings

logger = get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


class OpenAIService(ILLMService):
    """
    OpenAI GPT implementation of ILLMService.
    
    This service uses GPT-4o-mini for smart, cost-effective reasoning.
    Suitable for:
    - Query rewriting (understanding context)
    - Answer generation (coherent responses)
    - Document grading (quality assessment)
    
    Attributes:
        client: LangChain ChatOpenAI instance
        model: Model name (e.g., "gpt-4o-mini")
        temperature: Default temperature for generation
    
    Example:
        >>> service = OpenAIService(
        ...     api_key="sk-...",
        ...     model="gpt-4o-mini"
        ... )
        >>> response = service.generate("Rewrite: Nó phạt bao nhiêu?")
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        Initialize OpenAI service.
        
        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4o-mini)
            temperature: Sampling temperature (default: 0.1 for consistency)
            max_retries: Number of retries on failure
            timeout: Request timeout in seconds
        """
        self.model = model
        self.temperature = temperature
        
        try:
            self.client = ChatOpenAI(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_retries=max_retries,
                timeout=timeout
            )
            logger.info(
                "OpenAI service initialized",
                model=model,
                temperature=temperature
            )
        except Exception as e:
            logger.error(
                "Failed to initialize OpenAI service",
                error=str(e),
                model=model
            )
            raise LLMConnectionError(
                "Failed to initialize OpenAI service",
                provider="OpenAI",
                model=model
            ) from e
    
    def generate(self, prompt: str) -> str:
        """
        Generate text response from a prompt.
        
        Args:
            prompt: The user prompt/query
        
        Returns:
            Generated text response
        
        Raises:
            LLMConnectionError: If API call fails
            LLMOutputError: If output is invalid or empty
        
        Example:
            >>> response = service.generate(
            ...     "Viết lại câu hỏi: Nó phạt bao nhiêu?"
            ... )
            >>> print(response)
            "Lỗi vượt đèn đỏ với xe máy phạt bao nhiêu?"
        """
        try:
            logger.debug(
                "Generating text with OpenAI",
                model=self.model,
                prompt_length=len(prompt)
            )
            
            # Create message
            message = HumanMessage(content=prompt)
            
            # Invoke LLM
            response = self.client.invoke([message])
            
            # Extract content
            result = response.content.strip()
            
            if not result:
                raise LLMOutputError(
                    "OpenAI returned empty response",
                    output=result,
                    expected_format="non-empty text"
                )
            
            logger.debug(
                "OpenAI generation successful",
                output_length=len(result)
            )
            
            return result
            
        except LLMOutputError:
            # Re-raise our custom exceptions
            raise
            
        except Exception as e:
            logger.error(
                "OpenAI API call failed",
                error=str(e),
                error_type=type(e).__name__,
                prompt=prompt[:100]
            )
            raise LLMConnectionError(
                f"OpenAI API call failed: {str(e)}",
                provider="OpenAI",
                model=self.model
            ) from e
    
    def generate_structured(self, prompt: str, schema: Type[T]) -> T:
        """
        Generate structured output conforming to a Pydantic schema.
        
        This method uses OpenAI's function calling / structured output
        to ensure the response matches the expected schema.
        
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
            >>> class Intent(BaseModel):
            ...     intent: str
            ...     confidence: float
            >>> 
            >>> result = service.generate_structured(
            ...     "Classify: Vượt đèn đỏ phạt bao nhiêu?",
            ...     schema=Intent
            ... )
            >>> print(result.intent)  # "legal"
        """
        try:
            logger.debug(
                "Generating structured output with OpenAI",
                model=self.model,
                schema=schema.__name__,
                prompt_length=len(prompt)
            )
            
            # Create structured output client
            structured_llm = self.client.with_structured_output(schema)
            
            # Create message
            message = HumanMessage(content=prompt)
            
            # Invoke LLM with structured output
            result = structured_llm.invoke([message])
            
            # Validate result is instance of schema
            if not isinstance(result, schema):
                raise LLMOutputError(
                    f"Output is not instance of {schema.__name__}",
                    output=str(result),
                    expected_format=schema.__name__
                )
            
            logger.debug(
                "OpenAI structured generation successful",
                schema=schema.__name__,
                result=str(result)[:100]
            )
            
            return result
            
        except LLMOutputError:
            # Re-raise our custom exceptions
            raise
            
        except Exception as e:
            logger.error(
                "OpenAI structured generation failed",
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
    
    @classmethod
    def from_settings(cls) -> "OpenAIService":
        """
        Create OpenAI service from application settings.
        
        Returns:
            Configured OpenAIService instance
        
        Example:
            >>> service = OpenAIService.from_settings()
        """
        return cls(
            api_key=settings.OPENAI_API_KEY,
            model=settings.SMART_LLM_MODEL,
            temperature=settings.DEFAULT_TEMPERATURE
        )
