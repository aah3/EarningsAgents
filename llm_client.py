"""
llm_client.py  –  Flat-layout project root copy.

Unified LLM interface for Google Gemini, Anthropic Claude, and OpenAI GPT.

FIX 8 applied: _stream_anthropic falls back to _call_anthropic when
tool_choice is forced, because tool_use response blocks contain no text
tokens and stream.text_stream yields nothing.
"""

import os
import logging
import time
import threading
from typing import Optional, List, Any

logger = logging.getLogger(__name__)

FALLBACK_MAP = {
    "gemini": [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-flash-lite-latest"
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini"
    ],
    "anthropic": [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022"
    ]
}


class _ProviderRateLimiter:
    """Thread-safe minimum-interval rate limiter shared across all LLMClient instances."""

    def __init__(self):
        self._lock = threading.Lock()
        self._last: dict = {}
        self._global_pause_until: dict = {}
        gemini_rpm = int(os.getenv("GEMINI_RPM", "10"))
        self._DEFAULT_RPM = {
            "gemini":    gemini_rpm,
            "openai":    50,
            "anthropic": 50,
        }

    def wait(self, provider: str) -> None:
        """Block until it is safe to make one more call for *provider*."""
        rpm = self._DEFAULT_RPM.get(provider, 10)
        min_interval = 60.0 / rpm
        with self._lock:
            now = time.monotonic()
            pause_until = self._global_pause_until.get(provider, 0.0)
            if now < pause_until:
                time.sleep(pause_until - now)
                now = time.monotonic()
            elapsed = now - self._last.get(provider, 0.0)
            gap = min_interval - elapsed
            if gap > 0:
                time.sleep(gap)
            self._last[provider] = time.monotonic()

    def report_429(self, provider: str, penalty_seconds: float = 20.0):
        """Called when a 429 is hit; halts ALL threads for this provider."""
        with self._lock:
            new_pause = time.monotonic() + penalty_seconds
            if new_pause > self._global_pause_until.get(provider, 0.0):
                self._global_pause_until[provider] = new_pause
                logger.warning(
                    f"Global rate limit pause triggered for {provider} ({penalty_seconds}s)"
                )

    def clear_pause(self, provider: str) -> None:
        """Clears any active global pause for *provider*."""
        with self._lock:
            self._global_pause_until[provider] = 0.0


# Module-level singleton — shared by every LLMClient instance / thread.
_rate_limiter = _ProviderRateLimiter()


class LLMClient:
    """Unified interface for LLM analysis using Google Gemini, Anthropic, or OpenAI."""

    def __init__(self, api_key: str, provider: str = "gemini", model: Optional[str] = None):
        self.api_key = api_key
        self.provider = provider.lower()
        self.model = model
        self.client = self._initialize_client()

    def _initialize_client(self):
        """Initializes the appropriate client based on the selected provider."""
        if not self.api_key:
            logger.warning(f"No API key provided for LLM provider: {self.provider}")
            return None
        try:
            if self.provider == "gemini":
                from google import genai
                self.model = self.model or "gemini-flash-latest"
                return genai.Client(api_key=self.api_key)
            elif self.provider == "anthropic":
                from anthropic import Anthropic
                self.model = self.model or "claude-3-5-sonnet-20241022"
                return Anthropic(api_key=self.api_key)
            elif self.provider == "openai":
                from openai import OpenAI
                self.model = self.model or "gpt-4o"
                return OpenAI(api_key=self.api_key)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except ImportError as e:
            raise ImportError(
                f"Missing library for {self.provider}. Please install it. Error: {e}"
            )

    def _get_fallback_model(self, current_model: str) -> Optional[str]:
        """Returns the next fallback model in the chain for the current provider."""
        if not current_model:
            return None
        chain = FALLBACK_MAP.get(self.provider, [])
        normalized = current_model.lower()
        
        # Try to locate current model in the chain
        idx = -1
        for i, m in enumerate(chain):
            if m.lower() in normalized or normalized in m.lower():
                idx = i
                break
                
        if idx != -1:
            if idx + 1 < len(chain):
                return chain[idx + 1]
            else:
                return None
            
        # Hardcoded default fallbacks if the model name didn't match the chain
        if self.provider == "gemini":
            if "3.5-flash" in normalized:
                return "gemini-2.5-flash"
            if "2.5-flash" in normalized:
                return "gemini-2.0-flash"
            if "2.0-flash" in normalized:
                return "gemini-flash-latest"
            if "flash-latest" in normalized:
                return "gemini-flash-lite-latest"
        elif self.provider == "openai" and "mini" not in normalized:
            return "gpt-4o-mini"
        elif self.provider == "anthropic" and "haiku" not in normalized:
            return "claude-3-5-haiku-20241022"
            
        return None

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.3,
                 max_tokens: int = 2048, on_retry=None, **kwargs) -> str:
        """Generate a response (non-streaming). Retries on rate limits and triggers fallbacks on quota/transient errors."""
        if not self.client:
            raise RuntimeError(
                f"LLM client not initialized. Check API key for provider '{self.provider}'."
            )
        max_retries = 6
        base_delay = 5
        last_exc: Exception = RuntimeError("Unknown error")

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(base_delay * (2 ** (attempt - 1)))
                if self.provider == "gemini":
                    return self._call_gemini(system_prompt, user_prompt, temperature, max_tokens, **kwargs)
                elif self.provider == "anthropic":
                    return self._call_anthropic(system_prompt, user_prompt, temperature, max_tokens, **kwargs)
                elif self.provider == "openai":
                    return self._call_openai(system_prompt, user_prompt, temperature, max_tokens, **kwargs)
            except Exception as e:
                err_msg = str(e)
                is_quota = ("quota" in err_msg.lower() or "resource_exhausted" in err_msg or "limit" in err_msg.lower())
                is_transient = ("503" in err_msg or "500" in err_msg or "unavailable" in err_msg.lower() or "internal" in err_msg.lower())
                
                if is_quota or is_transient or "429" in err_msg or "rate_limit" in err_msg.lower():
                    # If it's a quota issue, OR if we've already retried at least once, try model fallback
                    if is_quota or attempt > 0:
                        fallback_model = self._get_fallback_model(self.model)
                        if fallback_model:
                            logger.warning(
                                f"Encountered quota/transient error on {self.provider} model '{self.model}': {err_msg}. "
                                f"Falling back to '{fallback_model}'..."
                            )
                            if on_retry:
                                on_retry(f"Falling back to {fallback_model} due to error: {err_msg[:60]}...")
                            self.model = fallback_model
                            _rate_limiter.clear_pause(self.provider)
                            continue
                        elif is_quota:
                            logger.error(f"Quota exceeded and no fallback model available for {self.provider} ({self.model}).")
                            raise e
                            
                    penalty = 20.0 * (2 ** attempt)
                    _rate_limiter.report_429(self.provider, penalty_seconds=penalty)
                    logger.warning(
                        f"Rate limit / transient error hit on {self.provider} (attempt {attempt+1}/{max_retries}). Retrying..."
                    )
                    if on_retry:
                        on_retry(f"API Error hit. Retrying attempt {attempt+1} of {max_retries}...")
                    last_exc = e
                    continue
                logger.error(f"Error calling {self.provider} API: {e}")
                raise

        raise RuntimeError(
            f"Maximum retries ({max_retries}) exceeded for {self.provider} generate(). "
            f"Last error: {last_exc}"
        ) from last_exc

    def generate_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.3,
                        max_tokens: int = 2048, on_retry=None, **kwargs):
        """Generate a streaming response, yielding text chunks, with quota and rate limit fallbacks."""
        if not self.client:
            raise RuntimeError(
                f"LLM client not initialized. Check API key for provider '{self.provider}'."
            )
        max_retries = 6
        base_delay = 5

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(base_delay * (2 ** (attempt - 1)))
                else:
                    time.sleep(1)
                if self.provider == "gemini":
                    yield from self._stream_gemini(system_prompt, user_prompt, temperature, max_tokens, **kwargs)
                elif self.provider == "anthropic":
                    yield from self._stream_anthropic(system_prompt, user_prompt, temperature, max_tokens, **kwargs)
                elif self.provider == "openai":
                    yield from self._stream_openai(system_prompt, user_prompt, temperature, max_tokens, **kwargs)
                break
            except Exception as e:
                err_msg = str(e)
                is_quota = ("quota" in err_msg.lower() or "resource_exhausted" in err_msg or "limit" in err_msg.lower())
                is_transient = ("503" in err_msg or "500" in err_msg or "unavailable" in err_msg.lower() or "internal" in err_msg.lower())
                
                if is_quota or is_transient or "429" in err_msg or "rate_limit" in err_msg.lower():
                    if is_quota or attempt > 0:
                        fallback_model = self._get_fallback_model(self.model)
                        if fallback_model:
                            logger.warning(
                                f"Encountered quota/transient error on {self.provider} streaming model '{self.model}': {err_msg}. "
                                f"Falling back to '{fallback_model}'..."
                            )
                            if on_retry:
                                on_retry(f"Streaming fallback to {fallback_model} due to error...")
                            self.model = fallback_model
                            _rate_limiter.clear_pause(self.provider)
                            continue
                        elif is_quota:
                            logger.error(f"Quota exceeded and no fallback model available for {self.provider} ({self.model}).")
                            raise e
                            
                    penalty = 20.0 * (2 ** attempt)
                    _rate_limiter.report_429(self.provider, penalty_seconds=penalty)
                    logger.warning(
                        f"Rate limit / transient error hit on {self.provider} streaming (attempt {attempt+1}/{max_retries}). Retrying..."
                    )
                    if on_retry:
                        on_retry(f"API Error hit in stream. Retrying attempt {attempt+1} of {max_retries}...")
                    if attempt == max_retries - 1:
                        raise RuntimeError(
                            f"Maximum retries ({max_retries}) exceeded for {self.provider} stream(). "
                            f"Last error: {e}"
                        ) from e
                    continue
                logger.error(f"Error streaming {self.provider} API: {e}")
                raise

    def chat(self, system_prompt: str, messages: List[dict], temperature: float = 0.3,
             max_tokens: int = 2048, on_retry=None) -> str:
        """Continue a multi-turn conversation with quota and rate limit fallbacks."""
        if not self.client:
            raise RuntimeError(
                f"LLM client not initialized. Check API key for provider '{self.provider}'."
            )
        max_retries = 6
        base_delay = 5
        last_exc: Exception = RuntimeError("Unknown error")

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(base_delay * (2 ** (attempt - 1)))
                if self.provider == "gemini":
                    return self._chat_gemini(system_prompt, messages, temperature, max_tokens)
                elif self.provider == "anthropic":
                    return self._chat_anthropic(system_prompt, messages, temperature, max_tokens)
                elif self.provider == "openai":
                    return self._chat_openai(system_prompt, messages, temperature, max_tokens)
            except Exception as e:
                err_msg = str(e)
                is_quota = ("quota" in err_msg.lower() or "resource_exhausted" in err_msg or "limit" in err_msg.lower())
                is_transient = ("503" in err_msg or "500" in err_msg or "unavailable" in err_msg.lower() or "internal" in err_msg.lower())
                
                if is_quota or is_transient or "429" in err_msg or "rate_limit" in err_msg.lower():
                    if is_quota or attempt > 0:
                        fallback_model = self._get_fallback_model(self.model)
                        if fallback_model:
                            logger.warning(
                                f"Encountered quota/transient error on {self.provider} chat model '{self.model}': {err_msg}. "
                                f"Falling back to '{fallback_model}'..."
                            )
                            if on_retry:
                                on_retry(f"Chat fallback to {fallback_model} due to error...")
                            self.model = fallback_model
                            _rate_limiter.clear_pause(self.provider)
                            continue
                        elif is_quota:
                            logger.error(f"Quota exceeded and no fallback model available for {self.provider} ({self.model}).")
                            raise e
                            
                    penalty = 20.0 * (2 ** attempt)
                    _rate_limiter.report_429(self.provider, penalty_seconds=penalty)
                    logger.warning(
                        f"Rate limit / transient error hit on {self.provider} chat (attempt {attempt+1}/{max_retries}). Retrying..."
                    )
                    if on_retry:
                        on_retry(f"API Error hit in chat. Retrying attempt {attempt+1} of {max_retries}...")
                    last_exc = e
                    continue
                logger.error(f"Error calling {self.provider} API: {e}")
                raise

        raise RuntimeError(
            f"Maximum retries ({max_retries}) exceeded for {self.provider} chat(). "
            f"Last error: {last_exc}"
        ) from last_exc

    # -------------------------------------------------------------------------
    # Provider-specific implementations
    # -------------------------------------------------------------------------

    def _call_gemini(self, sys_prompt, user_prompt, temperature, max_tokens, **kwargs):
        _rate_limiter.wait("gemini")
        config = {
            "system_instruction": sys_prompt,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if "generation_config" in kwargs:
            config.update(kwargs["generation_config"])
        response = self.client.models.generate_content(
            model=self.model, contents=user_prompt, config=config,
        )
        text = response.text
        if not text:
            raise ValueError(
                f"Gemini returned empty response. "
                f"Finish reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}"
            )
        return text

    def _call_anthropic(self, sys_prompt, user_prompt, temperature, max_tokens, **kwargs):
        _rate_limiter.wait("anthropic")
        call_kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": sys_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if "tools" in kwargs:
            call_kwargs["tools"] = kwargs["tools"]
        if "tool_choice" in kwargs:
            call_kwargs["tool_choice"] = kwargs["tool_choice"]
        message = self.client.messages.create(**call_kwargs)
        if "tools" in kwargs:
            import json
            for content in message.content:
                if content.type == "tool_use":
                    return json.dumps(content.input)
        return message.content[0].text

    def _call_openai(self, sys_prompt, user_prompt, temperature, max_tokens, **kwargs):
        _rate_limiter.wait("openai")
        call_kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if "response_format" in kwargs:
            call_kwargs["response_format"] = kwargs["response_format"]
        response = self.client.chat.completions.create(**call_kwargs)
        return response.choices[0].message.content

    def _stream_gemini(self, sys_prompt, user_prompt, temperature, max_tokens, **kwargs):
        _rate_limiter.wait("gemini")
        config = {
            "system_instruction": sys_prompt,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if "generation_config" in kwargs:
            config.update(kwargs["generation_config"])
        response = self.client.models.generate_content_stream(
            model=self.model,
            contents=user_prompt,
            config=config,
        )
        yielded_any = False
        for chunk in response:
            if chunk.text:
                yielded_any = True
                yield chunk.text
        if not yielded_any:
            raise ValueError(f"Gemini stream returned empty response for model {self.model}.")

    def _stream_anthropic(self, sys_prompt, user_prompt, temperature, max_tokens, **kwargs):
        # FIX 8 — When tool_choice is forced, the Anthropic response is a tool_use
        # block with no text tokens; stream.text_stream yields nothing and the caller
        # receives an empty string that fails json.loads("").
        # Fall back to a single non-streaming call and yield the result once.
        _rate_limiter.wait("anthropic")
        if "tools" in kwargs and "tool_choice" in kwargs:
            result = self._call_anthropic(sys_prompt, user_prompt, temperature, max_tokens, **kwargs)
            yield result
            return

        call_kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": sys_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if "tools" in kwargs:
            call_kwargs["tools"] = kwargs["tools"]
        if "tool_choice" in kwargs:
            call_kwargs["tool_choice"] = kwargs["tool_choice"]
        yielded_any = False
        with self.client.messages.stream(**call_kwargs) as stream:
            for text in stream.text_stream:
                if text:
                    yielded_any = True
                    yield text
        if not yielded_any:
            raise ValueError(f"Anthropic stream returned empty response for model {self.model}.")

    def _stream_openai(self, sys_prompt, user_prompt, temperature, max_tokens, **kwargs):
        _rate_limiter.wait("openai")
        call_kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if "response_format" in kwargs:
            call_kwargs["response_format"] = kwargs["response_format"]
        response = self.client.chat.completions.create(**call_kwargs)
        yielded_any = False
        for chunk in response:
            content = getattr(chunk.choices[0].delta, "content", None)
            if content:
                yielded_any = True
                yield content
        if not yielded_any:
            raise ValueError(f"OpenAI stream returned empty response for model {self.model}.")

    def _chat_gemini(self, sys_prompt, messages, temperature, max_tokens):
        _rate_limiter.wait("gemini")
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config={
                "system_instruction": sys_prompt,
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        text = response.text
        if not text:
            raise ValueError(
                f"Gemini returned empty response. "
                f"Finish reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}"
            )
        return text

    def _chat_anthropic(self, sys_prompt, messages, temperature, max_tokens):
        _rate_limiter.wait("anthropic")
        formatted_msgs = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "assistant"
            formatted_msgs.append({"role": role, "content": msg["content"]})
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=sys_prompt,
            messages=formatted_msgs,
        )
        return message.content[0].text

    def _chat_openai(self, sys_prompt, messages, temperature, max_tokens):
        _rate_limiter.wait("openai")
        formatted_msgs = [{"role": "system", "content": sys_prompt}]
        for msg in messages:
            role = "user" if msg["role"] == "user" else "assistant"
            formatted_msgs.append({"role": role, "content": msg["content"]})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_msgs,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
