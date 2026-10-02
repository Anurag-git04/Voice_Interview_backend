"""Provider-agnostic LLM interface with Groq integration."""
from typing import List, Dict, Tuple, Optional
import asyncio
import re
import logging
from groq import AsyncGroq, BadRequestError

from app.config import settings

logger = logging.getLogger(__name__)


class LLMProvider:
    """Base class for LLM providers."""
    
    def __init__(self):
        self.client = None
        self.model = None
    
    async def generate(
        self, 
        system: str, 
        history: List[Dict[str, str]]
    ) -> Tuple[str, float]:
        """
        Generate a response from the LLM.
        
        Args:
            system: System prompt
            history: List of message dicts with 'role' and 'content'
            
        Returns:
            Tuple of (response_text, latency_ms)
        """
        raise NotImplementedError


class GroqProvider(LLMProvider):
    """Groq LLM provider implementation with retry and fallback logic."""
    
    def __init__(self):
        super().__init__()
        # Initialize AsyncGroq client
        self.client = AsyncGroq(
            api_key=settings.groq_api_key
        )
        self.model = settings.groq_model
        # Fallback model for when primary model fails
        self.fallback_model = getattr(settings, 'groq_fallback_model', 'llama-3.1-8b-instant')
    
    def _salvage_text_from_error(self, error: Exception) -> Optional[str]:
        """
        Extract the intended text from a tool_use_failed error.
        The model sometimes writes its response in a tool-like format,
        but the actual content is usable.
        
        Args:
            error: The BadRequestError from Groq
            
        Returns:
            Salvaged text if found, None otherwise
        """
        try:
            body = getattr(error, "body", None) or {}
            err = body.get("error", body) if isinstance(body, dict) else {}
            failed_generation = err.get("failed_generation") or ""
            
            # Try to extract text from: {"name": "...", "arguments": ACTUAL_TEXT}
            match = re.search(r'"arguments":\s*(.*)\}\s*$', failed_generation, re.DOTALL)
            if match:
                text = match.group(1).strip()
                # Remove quotes if present
                if text.startswith('"') or text.startswith("'"):
                    text = text[1:]
                if text.endswith('"') or text.endswith("'"):
                    text = text[:-1]
                if text:
                    logger.info(f"Salvaged text from tool_use_failed error: {text[:100]}...")
                    return text
        except Exception as e:
            logger.debug(f"Could not salvage text from error: {e}")
        
        return None
    
    async def generate(
        self, 
        system: str, 
        history: List[Dict[str, str]]
    ) -> Tuple[str, float]:
        """Generate response using Groq API with retry and fallback logic."""
        import time
        
        # Build messages list
        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        
        # Try primary model first, then fallback
        models_to_try = [self.model]
        if self.fallback_model and self.fallback_model != self.model:
            models_to_try.append(self.fallback_model)
        
        last_error = None
        
        for model in models_to_try:
            # Try each model twice
            for attempt in range(2):
                start_time = time.time()
                
                try:
                    # Call Groq API asynchronously
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1024,
                    )
                    
                    latency_ms = (time.time() - start_time) * 1000
                    response_text = response.choices[0].message.content
                    
                    if response_text and response_text.strip():
                        if model != self.model:
                            logger.info(f"Fallback model {model} succeeded in {latency_ms:.2f}ms")
                        else:
                            logger.info(f"Groq response generated in {latency_ms:.2f}ms")
                        
                        # Update self.model to track which model succeeded
                        self.model = model
                        return response_text, latency_ms
                    
                except BadRequestError as e:
                    last_error = e
                    error_str = str(e)
                    
                    # Check if it's the tool_use_failed error
                    if "tool_use_failed" in error_str or "tool choice" in error_str.lower():
                        logger.warning(f"Model {model} tool_use_failed error on attempt {attempt + 1}")
                        
                        # Try to salvage the text
                        salvaged_text = self._salvage_text_from_error(e)
                        if salvaged_text:
                            latency_ms = (time.time() - start_time) * 1000
                            self.model = model
                            return salvaged_text, latency_ms
                    
                    # If this is the last attempt with this model, try fallback
                    if attempt == 1:
                        logger.warning(f"Model {model} failed after 2 attempts: {error_str[:200]}")
                        break
                    
                    # Short delay before retry (async sleep)
                    await asyncio.sleep(0.3)
                
                except Exception as e:
                    last_error = e
                    logger.error(f"Groq API error with model {model}: {e}")
                    break
        
        # All attempts failed
        logger.error(f"All Groq models failed. Last error: {last_error}")
        raise last_error


# Provider registry
PROVIDERS = {
    "groq": GroqProvider,
}


def get_provider(provider_name: str = "groq") -> LLMProvider:
    """
    Get an LLM provider instance.
    
    Args:
        provider_name: Name of the provider (default: "groq")
        
    Returns:
        LLMProvider instance
    """
    provider_class = PROVIDERS.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    return provider_class()


async def generate(
    system: str,
    history: List[Dict[str, str]],
    provider_name: str = "groq",
    fallback: bool = False
) -> Tuple[str, str, str, float]:
    """
    Generate a response with optional fallback to another provider.
    
    Args:
        system: System prompt
        history: Conversation history
        provider_name: Name of the provider to use
        fallback: Whether to fallback to another provider on error
        
    Returns:
        Tuple of (response_text, provider_used, model_used, latency_ms)
    """
    provider = get_provider(provider_name)
    
    try:
        response_text, latency_ms = await provider.generate(system, history)
        return response_text, provider_name, provider.model, latency_ms
    except Exception as e:
        if fallback:
            # For now, just re-raise since we only have one provider
            # In Phase 5, this will try Gemini as fallback
            logger.error(f"Provider {provider_name} failed and no fallback available: {e}")
            raise
        else:
            raise
