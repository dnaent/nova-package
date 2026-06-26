"""
Provider-aware LLM router.

Routes a single-turn completion to the provider that owns the resolved model name.
Includes support for token budgeting, retries, and cross-provider failover.
"""
import asyncio
import contextvars
import logging
import os

from .model_config_utils import get_model_provider
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class TokenBudgetExceeded(Exception):
    """Raised when a blueprint's estimated LLM token budget is exhausted."""

class _Budget:
    __slots__ = ("cap", "used", "calls")

    def __init__(self, cap: int):
        self.cap = cap
        self.used = 0
        self.calls = 0

    def charge(self, estimate: int):
        self.calls += 1
        if self.cap and (self.used + estimate) > self.cap:
            raise TokenBudgetExceeded(
                f"Per-context token budget exceeded: {self.used}+{estimate} > {self.cap} "
                f"(after {self.calls} LLM calls)"
            )
        self.used += estimate

_budget_var: contextvars.ContextVar = contextvars.ContextVar("llm_budget", default=None)

def set_budget(cap: int) -> _Budget:
    """Start a fresh per-context budget. cap<=0 disables."""
    budget = _Budget(cap)
    _budget_var.set(budget)
    return budget

def current_budget():
    return _budget_var.get()

def _estimate_tokens(system_prompt: str, user_prompt: str, max_tokens: int) -> int:
    text_len = len(system_prompt or "") + len(user_prompt or "")
    return (text_len // 4) + int(max_tokens or 0)

try:
    import anthropic
    _RETRYABLE_ANTHROPIC = (
        anthropic.APIConnectionError,
        anthropic.RateLimitError,
        anthropic.InternalServerError,
    )
except Exception:
    anthropic = None
    _RETRYABLE_ANTHROPIC = tuple()

try:
    import openai
    _RETRYABLE_OPENAI = (
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.InternalServerError,
    )
except Exception:
    openai = None
    _RETRYABLE_OPENAI = tuple()

try:
    from google.api_core import exceptions as _gax_exceptions
    _RETRYABLE_GOOGLE = (
        _gax_exceptions.ResourceExhausted,
        _gax_exceptions.ServiceUnavailable,
        _gax_exceptions.InternalServerError,
    )
except Exception:
    _RETRYABLE_GOOGLE = tuple()

OPENAI_SECRET_NAME = os.environ.get("OPENAI_SECRET_NAME", "openai-api-key")

_RETRY_KW = dict(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
)

_RETRY_KW_GOOGLE = dict(
    wait=wait_exponential(multiplier=2, min=10, max=60),
    stop=stop_after_attempt(6),
)

def _require_key(secret_manager, secret_name, provider_label):
    key = secret_manager.get_secret(secret_name) if secret_manager is not None else None
    if not key:
        raise ValueError(f"{provider_label} API key not found (secret '{secret_name}').")
    return key

@retry(retry=retry_if_exception_type(_RETRYABLE_ANTHROPIC), **_RETRY_KW)
def _complete_anthropic(secret_manager, model_name, system_prompt, user_prompt, max_tokens, json_mode):
    if anthropic is None:
        raise RuntimeError("anthropic SDK not available")
    
    # Can configure standard client or vertex client depending on environment
    client = anthropic.AnthropicVertex(
        project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        region=os.environ.get("ANTHROPIC_REGION", "global"),
        max_retries=0,
    )
    system = system_prompt or ""
    if json_mode:
        system = system + "\n\nRespond with a single valid JSON object and nothing else."
    resp = client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    parts = [b.text for b in (resp.content or []) if getattr(b, "type", None) == "text"]
    text = "".join(parts).strip()
    if not text:
        raise ValueError("Anthropic returned an empty/non-text response.")
    return text


@retry(retry=retry_if_exception_type(_RETRYABLE_OPENAI), **_RETRY_KW)
def _complete_openai(secret_manager, model_name, system_prompt, user_prompt, max_tokens, temperature, json_mode):
    if openai is None:
        raise RuntimeError("openai SDK not available")
    client = openai.OpenAI(api_key=_require_key(secret_manager, OPENAI_SECRET_NAME, "OpenAI"), max_retries=0)
    kwargs = {
        "model": model_name,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt or ""},
            {"role": "user", "content": user_prompt},
        ],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
    if not text:
        raise ValueError("OpenAI returned an empty response.")
    return text


@retry(retry=retry_if_exception_type(_RETRYABLE_GOOGLE), **_RETRY_KW_GOOGLE)
def _complete_google(model_name, system_prompt, user_prompt, max_tokens, temperature, json_mode):
    import vertexai
    from vertexai.generative_models import GenerativeModel
    vertexai.init(project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
                  location=os.environ.get("GEMINI_LOCATION", "global"))
    
    gen_cfg = {"max_output_tokens": max(max_tokens, 8192), "temperature": temperature}
    if json_mode:
        gen_cfg["response_mime_type"] = "application/json"
    model = (
        GenerativeModel(model_name, system_instruction=system_prompt)
        if system_prompt else GenerativeModel(model_name)
    )
    resp = model.generate_content(user_prompt, generation_config=gen_cfg)
    try:
        text = (resp.text or "").strip()
    except Exception:
        parts = []
        for cand in (getattr(resp, "candidates", None) or []):
            content = getattr(cand, "content", None)
            for part in (getattr(content, "parts", None) or []):
                t = getattr(part, "text", None)
                if t:
                    parts.append(t)
        text = "".join(parts).strip()
    if not text:
        finish = ", ".join(
            str(getattr(c, "finish_reason", "?")) for c in (getattr(resp, "candidates", None) or [])
        )
        raise ValueError(f"Google returned an empty response (finish_reason: {finish or 'none'}).")
    return text


def complete(secret_manager, model_name, system_prompt, user_prompt, max_tokens=1024,
             temperature=0.7, json_mode=False, task_id="", context_id=""):
    """Route a single-turn completion to the provider that owns ``model_name``."""
    provider = get_model_provider(model_name)

    budget = _budget_var.get()
    if budget is not None:
        budget.charge(_estimate_tokens(system_prompt, user_prompt, max_tokens))

    logger.info(
        f"LLM router -> provider={provider} model={model_name} (task={task_id}, context={context_id})"
    )
    try:
        if provider == "anthropic":
            return _complete_anthropic(secret_manager, model_name, system_prompt, user_prompt, max_tokens, json_mode)
        if provider == "openai":
            return _complete_openai(secret_manager, model_name, system_prompt, user_prompt, max_tokens, temperature, json_mode)
        if provider == "google":
            return _complete_google(model_name, system_prompt, user_prompt, max_tokens, temperature, json_mode)
        raise ValueError(f"Unknown provider for model '{model_name}'")
    except Exception as e_primary:
        fallback_model = os.environ.get("LLM_FALLBACK_MODEL", "gemini-2.5-flash")
        if provider == "google" or model_name == fallback_model:
            raise
        logger.warning(
            f"LLM router: provider '{provider}' failed for model '{model_name}' "
            f"({type(e_primary).__name__}: {str(e_primary)[:200]}); automatic failover -> {fallback_model} "
            f"(task={task_id}, context={context_id})"
        )
        return _complete_google(fallback_model, system_prompt, user_prompt, max_tokens, temperature, json_mode)


async def complete_async(*args, **kwargs):
    """Async wrapper for complete()."""
    return await asyncio.to_thread(complete, *args, **kwargs)
