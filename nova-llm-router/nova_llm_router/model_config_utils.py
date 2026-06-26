"""
Utility functions for dynamic agent model configuration management.
"""
import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

# Constants
MODEL_MAPPING_FILE = os.path.join(os.path.dirname(__file__), "model_mapping.json")

DEFAULT_MODELS = {
    "agent_type_a": "gemini-2.5-flash",
    "agent_type_b": "gemini-2.5-flash",
    "default": "gemini-2.5-flash"
}

TIER_MAPPING = {
    "free_trial": "free",
    "pro_tier": "professional",
    "professional_tier": "professional",
    "ultra_tier": "ultra",
    "enterprise_tier": "enterprise"
}

MODEL_MAPPING = None

def load_model_mapping():
    """Load model mapping from JSON file"""
    global MODEL_MAPPING
    try:
        with open(MODEL_MAPPING_FILE, 'r') as f:
            MODEL_MAPPING = json.load(f)
        logger.info(f"Loaded model mapping from {MODEL_MAPPING_FILE}")
    except Exception as e:
        logger.warning(f"Failed to load model mapping from {MODEL_MAPPING_FILE}: {e}")
        MODEL_MAPPING = None

load_model_mapping()

def resolve_alias(model_str: str) -> str:
    """Resolve alias to actual model name using MODEL_MAPPING"""
    if not MODEL_MAPPING:
        return model_str

    if model_str.startswith("aliases."):
        alias_key = model_str.split("aliases.")[1]
        return MODEL_MAPPING.get("aliases", {}).get(alias_key, model_str)
    return model_str

async def get_user_model_for_agent(user_id: str, agent_id: str, user_tier: str = "free_trial") -> str:
    """
    Get the user-specific model configuration for an agent using centralized configuration.
    """
    global MODEL_MAPPING
    if MODEL_MAPPING is None:
        load_model_mapping()

    if MODEL_MAPPING:
        try:
            if agent_id in MODEL_MAPPING.get("fixed_models", {}):
                model = MODEL_MAPPING["fixed_models"][agent_id]
                return model

            normalized_tier = TIER_MAPPING.get(user_tier, user_tier)
            if normalized_tier not in MODEL_MAPPING.get("tiers", {}):
                normalized_tier = "free"

            tier_config = MODEL_MAPPING.get("tiers", {}).get(normalized_tier, {})
            model_ref = tier_config.get(agent_id)

            if model_ref:
                return resolve_alias(model_ref)

        except Exception as e:
             logger.error(f"Error resolving model from centralized config: {e}")

    return DEFAULT_MODELS.get(agent_id, "gemini-2.5-flash")

def get_model_provider(model_name: str) -> str:
    """Determine the provider for a given model name."""
    if model_name.startswith("claude"):
        return "anthropic"
    elif model_name.startswith("gpt") or model_name.startswith("o1"):
        return "openai"
    elif model_name.startswith("gemini"):
        return "google"
    return "anthropic"

class ModelEndpointManager:
    """Manages real LLM API endpoints"""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.secret_client = secretmanager.SecretManagerServiceClient()
        self._api_keys = {}
        self._endpoints = {
            "anthropic": "https://api.anthropic.com/v1/messages",
            "openai": "https://api.openai.com/v1/chat/completions",
            "google": "https://generativelanguage.googleapis.com/v1beta/models"
        }

    async def initialize(self):
        """Initialize API keys from Google Secret Manager"""
        try:
            await self._load_api_keys()
        except Exception as e:
            logger.error(f"Failed to initialize model endpoint manager: {e}")
            raise

    async def _load_api_keys(self):
        secret_names = {
            "anthropic": "anthropic-api-key",
            "openai": "openai-api-key",
            "google": "google-ai-api-key"
        }

        for provider, secret_name in secret_names.items():
            try:
                name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                response = self.secret_client.access_secret_version(request={"name": name})
                self._api_keys[provider] = response.payload.data.decode("UTF-8")
            except Exception as e:
                self._api_keys[provider] = None

    async def call_model(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000,
        temperature: float = 0.7,
        user_tier: str = "free_trial",
        **kwargs
    ) -> Dict[str, Any]:
        """Make a request to the specified model"""
        provider = get_model_provider(model_name)

        if provider not in self._api_keys or not self._api_keys[provider]:
            raise ValueError(f"No API key available for provider: {provider}")

        try:
            if provider == "anthropic":
                return await self._call_anthropic(model_name, messages, max_tokens, temperature, **kwargs)
            elif provider == "openai":
                return await self._call_openai(model_name, messages, max_tokens, temperature, **kwargs)
            elif provider == "google":
                return await self._call_google(model_name, messages, max_tokens, temperature, **kwargs)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
        except Exception as e:
            logger.error(f"Model call failed for {model_name}: {e}")
            raise

    async def _call_anthropic(self, model_name: str, messages: List[Dict], max_tokens: int, temperature: float, **kwargs) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._api_keys["anthropic"],
            "anthropic-version": "2023-06-01"
        }
        system_message = ""
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append({"role": msg["role"], "content": msg["content"]})
        payload = {
            "model": model_name,
            "messages": claude_messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if system_message:
            payload["system"] = system_message

        async with aiohttp.ClientSession() as session:
            async with session.post(self._endpoints["anthropic"], headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "content": data["content"][0]["text"],
                        "usage": data.get("usage", {}),
                        "model": data.get("model", model_name),
                        "provider": "anthropic"
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API error {response.status}: {error_text}")

    async def _call_openai(self, model_name: str, messages: List[Dict], max_tokens: int, temperature: float, **kwargs) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_keys['openai']}"
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self._endpoints["openai"], headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "content": data["choices"][0]["message"]["content"],
                        "usage": data.get("usage", {}),
                        "model": data.get("model", model_name),
                        "provider": "openai"
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error {response.status}: {error_text}")

    async def _call_google(self, model_name: str, messages: List[Dict], max_tokens: int, temperature: float, **kwargs) -> Dict[str, Any]:
        gemini_contents = []
        for msg in messages:
            if msg["role"] == "system":
                gemini_contents.append({"role": "user", "parts": [{"text": f"System: {msg['content']}"}]})
            elif msg["role"] == "user":
                gemini_contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                gemini_contents.append({"role": "model", "parts": [{"text": msg["content"]}]})
        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature
            }
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self._api_keys['google']}"
        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if "candidates" in data and len(data["candidates"]) > 0:
                        content = data["candidates"][0]["content"]["parts"][0]["text"]
                        return {
                            "content": content,
                            "usage": data.get("usageMetadata", {}),
                            "model": model_name,
                            "provider": "google"
                        }
                    else:
                        raise Exception(f"No valid response from Gemini: {data}")
                else:
                    error_text = await response.text()
                    raise Exception(f"Google API error {response.status}: {error_text}")

async def call_agent_model(
    project_id: str,
    user_id: str,
    agent_id: str,
    messages: List[Dict[str, str]],
    user_tier: str = "free_trial",
    **kwargs
) -> Dict[str, Any]:
    """
    Cost-optimized convenience function to call an agent's configured model
    """
    model_name = await get_user_model_for_agent(user_id, agent_id, user_tier)
    endpoint_manager = await get_endpoint_manager(project_id)
    result = await endpoint_manager.call_model(
        model_name=model_name,
        messages=messages,
        user_tier=user_tier,
        **kwargs
    )
    result["agent_id"] = agent_id
    result["user_id"] = user_id
    result["user_tier"] = user_tier
    result["configured_model"] = model_name
    return result

_endpoint_manager: Optional[ModelEndpointManager] = None

async def get_endpoint_manager(project_id: str) -> ModelEndpointManager:
    global _endpoint_manager
    if _endpoint_manager is None:
        _endpoint_manager = ModelEndpointManager(project_id)
        await _endpoint_manager.initialize()
    return _endpoint_manager
