"""
providers.py — AI Provider configurations.

Defines base URLs, models, and settings for each supported AI provider.
All providers use OpenAI-compatible APIs.
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider."""
    id: str
    name: str
    base_url: str
    api_key_env: str  # Environment variable name for API key
    models: List[str]
    default_model: str
    embedding_model: str
    requires_api_key: bool = True
    free_tier_info: str = ""


# Provider configurations
PROVIDERS: Dict[str, ProviderConfig] = {
    "openai": ProviderConfig(
        id="openai",
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        default_model="gpt-4o",
        embedding_model="text-embedding-3-small",
        free_tier_info="Paid only - No free tier"
    ),
    "openrouter": ProviderConfig(
        id="openrouter",
        name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        models=[
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.5-flash",
            "meta-llama/llama-3.3-70b-instruct",
            "nvidia/nemotron-3-ultra-550b-a55b:free",
            "deepseek/deepseek-chat",
        ],
        default_model="openai/gpt-4o-mini",
        embedding_model="openai/text-embedding-3-small",
        free_tier_info="50 req/day free, 1000 req/day with $10+ balance"
    ),
    "nvidia": ProviderConfig(
        id="nvidia",
        name="NVIDIA NIM",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_API_KEY",
        models=[
            "meta/llama-3.3-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "nvidia/nemotron-3-ultra-550b-a55b",
            "nvidia/nemotron-3-super-120b-a12b",
            "deepseek-ai/deepseek-r1",
            "qwen/qwen3-235b-a22b",
        ],
        default_model="meta/llama-3.3-70b-instruct",
        embedding_model="nvidia/nv-embedqa-e5-v5",
        free_tier_info="40 RPM free, no daily token cap"
    ),
    "groq": ProviderConfig(
        id="groq",
        name="Groq",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        models=[
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "deepseek-r1-distill-70b",
        ],
        default_model="llama-3.3-70b-versatile",
        embedding_model="llama-3.3-70b-versatile",  # Groq doesn't have embedding models
        free_tier_info="30 RPM free, 14,400 req/day"
    ),
    "cerebras": ProviderConfig(
        id="cerebras",
        name="Cerebras",
        base_url="https://api.cerebras.ai/v1",
        api_key_env="CEREBRAS_API_KEY",
        models=[
            "llama-3.3-70b",
            "llama-3.1-8b",
            "qwen-2.5-32b",
        ],
        default_model="llama-3.3-70b",
        embedding_model="llama-3.3-70b",  # Cerebras doesn't have embedding models
        free_tier_info="1M tokens/day free, extremely fast inference"
    ),
    "gemini": ProviderConfig(
        id="gemini",
        name="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key_env="GEMINI_API_KEY",
        models=[
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ],
        default_model="gemini-2.5-flash",
        embedding_model="text-embedding-004",
        free_tier_info="1500 req/day free, no credit card required"
    ),
    "opencode": ProviderConfig(
        id="opencode",
        name="OpenCode",
        base_url="",
        api_key_env="OPENCODE_API_KEY",
        models=[],
        default_model="",
        embedding_model="",
        requires_api_key=True,
        free_tier_info="Configure your OpenCode-compatible endpoint and API key"
    ),
    "custom": ProviderConfig(
        id="custom",
        name="Custom Provider",
        base_url="",
        api_key_env="CUSTOM_API_KEY",
        models=[],
        default_model="",
        embedding_model="",
        requires_api_key=True,
        free_tier_info="Configure your own OpenAI-compatible endpoint"
    ),
}


def get_provider(provider_id: str) -> ProviderConfig:
    """Get provider configuration by ID."""
    if provider_id not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider_id}")
    return PROVIDERS[provider_id]


def get_all_providers() -> List[Dict[str, Any]]:
    """Get all providers as a list of dicts for API response."""
    return [
        {
            "id": p.id,
            "name": p.name,
            "base_url": p.base_url,
            "models": p.models,
            "default_model": p.default_model,
            "embedding_model": p.embedding_model,
            "requires_api_key": p.requires_api_key,
            "free_tier_info": p.free_tier_info,
        }
        for p in PROVIDERS.values()
    ]


def get_provider_base_url(provider_id: str) -> str:
    """Get the base URL for a provider."""
    provider = get_provider(provider_id)
    return provider.base_url


def get_provider_models(provider_id: str) -> List[str]:
    """Get available models for a provider."""
    provider = get_provider(provider_id)
    return provider.models
