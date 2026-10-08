"""
routes/settings.py — Settings management endpoints.

Provides endpoints for:
  - Getting current provider settings
  - Updating provider settings
  - Testing provider connections
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings, get_all_providers, get_provider
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ProviderUpdateRequest(BaseModel):
    """Request model for updating provider settings."""
    provider: str = Field(..., description="Provider ID (openai, openrouter, nvidia, groq, cerebras, gemini, custom)")
    api_key: Optional[str] = Field(None, description="API key for the provider")
    model: Optional[str] = Field(None, description="Model to use")
    base_url: Optional[str] = Field(None, description="Custom base URL (for custom provider only)")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens for responses")
    temperature: Optional[float] = Field(None, description="Temperature for responses")


class ProviderTestRequest(BaseModel):
    """Request model for testing provider connection."""
    provider: str = Field(..., description="Provider ID to test")
    api_key: str = Field(..., description="API key to test")
    base_url: Optional[str] = Field(None, description="Custom base URL")


@router.get("/providers")
async def list_providers():
    """List all available AI providers with their configurations."""
    return {
        "providers": get_all_providers(),
        "current_provider": settings.AI_PROVIDER,
    }


@router.get("/current")
async def get_current_settings():
    """Get current provider settings (synced from Redis across all workers)."""
    # Sync from Redis so all workers report the same state
    try:
        from app.services.redis_service import redis_service
        saved = await redis_service.load_settings()
        if saved:
            for key, value in saved.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
    except Exception:
        pass

    provider = get_provider(settings.AI_PROVIDER)
    
    return {
        "provider": settings.AI_PROVIDER,
        "provider_name": provider.name,
        "api_key_set": bool(settings.get_active_api_key()),
        "model": settings.get_active_model(),
        "base_url": settings.get_active_base_url(),
        "max_tokens": settings.OPENAI_MAX_TOKENS,
        "temperature": settings.OPENAI_TEMPERATURE,
        "available_models": provider.models,
    }


@router.put("/update")
async def update_settings(request: ProviderUpdateRequest):
    """Update provider settings — mutates in-memory settings and persists to Redis."""
    try:
        provider = get_provider(request.provider)

        # ── Mutate the in-memory settings singleton ──────────────────────
        settings.AI_PROVIDER = request.provider

        if request.api_key is not None:
            setattr(settings, provider.api_key_env, request.api_key)

        if request.model is not None:
            model_attr = f"{request.provider.upper()}_MODEL"
            if hasattr(settings, model_attr):
                setattr(settings, model_attr, request.model)
            if request.provider == "openai":
                settings.OPENAI_MODEL = request.model

        if request.base_url is not None and request.provider in ("custom", "opencode"):
            base_url_attr = f"{request.provider.upper()}_BASE_URL"
            if hasattr(settings, base_url_attr):
                setattr(settings, base_url_attr, request.base_url)

        if request.max_tokens is not None:
            settings.OPENAI_MAX_TOKENS = request.max_tokens

        if request.temperature is not None:
            settings.OPENAI_TEMPERATURE = request.temperature

        # ── Persist to Redis (survives restarts) ──────────────────────────
        from app.services.redis_service import redis_service
        await redis_service.save_settings({
            "AI_PROVIDER": settings.AI_PROVIDER,
            "OPENAI_API_KEY": settings.OPENAI_API_KEY,
            "OPENROUTER_API_KEY": settings.OPENROUTER_API_KEY,
            "NVIDIA_API_KEY": settings.NVIDIA_API_KEY,
            "GROQ_API_KEY": settings.GROQ_API_KEY,
            "CEREBRAS_API_KEY": settings.CEREBRAS_API_KEY,
            "GEMINI_API_KEY": settings.GEMINI_API_KEY,
            "MIMO_API_KEY": settings.MIMO_API_KEY,
            "OPENCODE_API_KEY": settings.OPENCODE_API_KEY,
            "CUSTOM_API_KEY": settings.CUSTOM_API_KEY,
            "OPENROUTER_MODEL": settings.OPENROUTER_MODEL,
            "NVIDIA_MODEL": settings.NVIDIA_MODEL,
            "GROQ_MODEL": settings.GROQ_MODEL,
            "CEREBRAS_MODEL": settings.CEREBRAS_MODEL,
            "GEMINI_MODEL": settings.GEMINI_MODEL,
            "MIMO_MODEL": settings.MIMO_MODEL,
            "OPENCODE_MODEL": settings.OPENCODE_MODEL,
            "CUSTOM_MODEL": settings.CUSTOM_MODEL,
            "CUSTOM_BASE_URL": settings.CUSTOM_BASE_URL,
            "OPENCODE_BASE_URL": settings.OPENCODE_BASE_URL,
            "OPENAI_MAX_TOKENS": settings.OPENAI_MAX_TOKENS,
            "OPENAI_TEMPERATURE": settings.OPENAI_TEMPERATURE,
        })

        logger.info("Settings updated: provider=%s, model=%s", request.provider, request.model)

        return {
            "success": True,
            "message": f"Settings updated to use {provider.name}",
            "provider": request.provider,
            "model": request.model or provider.default_model,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to update settings: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


@router.post("/test")
async def test_provider(request: ProviderTestRequest):
    """Test provider connection with the given API key."""
    try:
        provider = get_provider(request.provider)
        
        # For custom provider, use provided base_url
        base_url = request.base_url if request.provider == "custom" else provider.base_url
        
        if not base_url:
            raise HTTPException(status_code=400, detail="Base URL is required for custom provider")
        
        # Test the connection by making a simple API call
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=request.api_key,
            base_url=base_url,
        )
        
        # Try to list models or make a simple completion
        try:
            # For OpenAI-compatible providers, try to list models
            models = await client.models.list()
            model_list = [m.id for m in models.data[:5]]  # Get first 5 models
            
            return {
                "success": True,
                "message": f"Successfully connected to {provider.name}",
                "available_models": model_list,
                "provider": request.provider,
            }
        except Exception as e:
            # Some providers don't support /models endpoint, try a simple completion
            try:
                response = await client.chat.completions.create(
                    model=provider.default_model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=10,
                )
                
                return {
                    "success": True,
                    "message": f"Successfully connected to {provider.name}",
                    "response": response.choices[0].message.content,
                    "provider": request.provider,
                }
            except Exception as inner_e:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Failed to connect to {provider.name}: {str(inner_e)}"
                )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Provider test failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Provider test failed: {str(e)}")


@router.get("/models/{provider_id}")
async def get_provider_models(provider_id: str):
    """Get available models for a specific provider."""
    try:
        provider = get_provider(provider_id)
        return {
            "provider": provider_id,
            "models": provider.models,
            "default_model": provider.default_model,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider_id}")
