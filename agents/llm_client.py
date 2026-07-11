import os
import logging
import time
import threading
from typing import Optional, List, Any

# Configure logging
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
    """Thread-safe minimum-interval rate limiter shared across all LLMClient instances.

    Ensures we never fire more than N calls per minute to a provider,
    regardless of how many parallel threads are running ReAct loops.
    """
    # Conservative limits (calls/min).  Gemini free tier is 10-15 RPM;
    # we use 10 to leave headroom for retries.
    def __init__(self):
        self._lock = threading.Lock()
        self._last: dict = {}  # provider -> last call monotonic time
        self._global_pause_until: dict = {}  # provider -> paused until this monotonic time
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
            
            # Enforce global pause if we recently hit a 429
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
            # Only extend the pause, don't shorten it if another thread already reported
            if new_pause > self._global_pause_until.get(provider, 0.0):
                self._global_pause_until[provider] = new_pause
                logger.warning(f"Global rate limit pause triggered for {provider} ({penalty_seconds}s)")

    def clear_pause(self, provider: str) -> None:
        """Clears any active global pause for *provider*."""
        with self._lock:
            self._global_pause_until[provider] = 0.0


# Module-level singleton — shared by every LLMClient instance / thread.
_rate_limiter = _ProviderRateLimiter()

class LLMClient:
    """
    A unified interface for LLM analysis using Google Gemini, Anthropic, or OpenAI.
    """
    
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
            raise ImportError(f"Missing library for {self.provider}. Please install it. Error: {e}")

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

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.3,
                 max_tokens: int = 2048, on_retry=None, **kwargs) -> str:
        """
        Generates content from the LLM based on system and user prompts.
        Includes basic retry logic for rate limits and fallbacks for quota/transient errors.
        Raises RuntimeError if the client is not initialized or retries are exhausted.
        """
        if not self.client:
            raise RuntimeError(
                f"LLM client not initialized. Check API key for provider '{self.provider}'."
            )

        max_retries = 6
        base_delay = 5  # seconds
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
            f"Maximum retries ({max_retries}) exceeded for {self.provider} generate(). Last error: {last_exc}"
        ) from last_exc

    def generate_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.3,
                        max_tokens: int = 2048, on_retry=None, **kwargs):
        """
        Generates content from the LLM based on system and user prompts, yielding chunks as they arrive, with quota/transient fallbacks.
        """
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
                    time.sleep(1)  # Small initial pause

                if self.provider == "gemini":
                    yield from self._stream_gemini(system_prompt, user_prompt, temperature, max_tokens, **kwargs)
                elif self.provider == "anthropic":
                    yield from self._stream_anthropic(system_prompt, user_prompt, temperature, max_tokens, **kwargs)
                elif self.provider == "openai":
                    yield from self._stream_openai(system_prompt, user_prompt, temperature, max_tokens, **kwargs)

                # If successful, exit the retry loop
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
                            f"Maximum retries ({max_retries}) exceeded for {self.provider} stream(). Last error: {e}"
                        ) from e
                    continue

                logger.error(f"Error streaming {self.provider} API: {e}")
                raise

    def chat(self, system_prompt: str, messages: List[dict], temperature: float = 0.3,
             max_tokens: int = 2048, on_retry=None) -> str:
        """
        Continues a conversation using a list of messages: [{"role": "user"|"model", "content": "..."}] with quota/transient fallbacks.
        Raises RuntimeError if the client is not initialized or retries are exhausted.
        """
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
            f"Maximum retries ({max_retries}) exceeded for {self.provider} chat(). Last error: {last_exc}"
        ) from last_exc

    # -------------------------------------------------------------------------
    # Provider-specific call implementations
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

        # If a tool was forced, return its input as a JSON string
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
        _rate_limiter.wait("anthropic")
        # When tool_choice is forced (structured output via tool-use), the response is a
        # tool_use block with no text tokens — streaming yields nothing useful.
        # Fall back to a single non-streaming call and yield the result once.
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


# ============================================================================
# QUICK SMOKE-TEST  -  python agents/llm_client.py
# ============================================================================

if __name__ == "__main__":
    import os
    import sys
    import time

    # Ensure project root is on path
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)

    # Load .env from project root regardless of CWD
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(usecwd=False), override=True)  # .env wins over stale shell vars

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    # Strip inline comments (e.g. 'openai  # gemini | openai | ...') before use
    provider = os.getenv("LLM_PROVIDER", "gemini").split("#")[0].strip().lower()
    model    = os.getenv("LLM_MODEL_NAME") or None
    key_map  = {
        "gemini":    os.getenv("GEMINI_API_KEY"),
        "openai":    os.getenv("OPENAI_API_KEY"),
        "anthropic": os.getenv("ANTHROPIC_API_KEY"),
    }
    api_key = key_map.get(provider)

    SEP = "=" * 60
    print("")
    print(SEP)
    print("  LLMClient smoke-test")
    print(f"  Provider : {provider}")
    print(f"  Model    : {model or '(default)'}")
    print(f"  API key  : {'[OK]' if api_key else '[MISSING]'}")
    print(SEP)
    print("")

    if not api_key:
        print(f"[WARNING] No API key found for provider '{provider}'.")
        print(f"          Set {provider.upper()}_API_KEY in your .env or environment.")
        print("          Skipping live API tests.")
        sys.exit(0)

    client = LLMClient(api_key=api_key, provider=provider, model=model)

    SYS  = "You are a concise assistant. Reply in one sentence only."
    USER = "What is the capital of France?"

    # -- Test 1: generate() --------------------------------------------------
    print("-- Test 1: generate() -----------------------------------------")
    t0 = time.perf_counter()
    result = client.generate(system_prompt=SYS, user_prompt=USER, max_tokens=64)
    elapsed = time.perf_counter() - t0
    print(f"   Response ({elapsed:.2f}s): {result!r}")
    print("")

    # -- Test 2: generate_stream() -------------------------------------------
    print("-- Test 2: generate_stream() ----------------------------------")
    t0 = time.perf_counter()
    chunks = []
    print("   Chunks: ", end="", flush=True)
    for chunk in client.generate_stream(system_prompt=SYS, user_prompt=USER, max_tokens=64):
        print(".", end="", flush=True)
        chunks.append(chunk)
    elapsed = time.perf_counter() - t0
    full = "".join(chunks)
    print(f"\n   Full ({elapsed:.2f}s): {full!r}")
    print("")

    # -- Test 3: chat() ------------------------------------------------------
    print("-- Test 3: chat() ---------------------------------------------")
    msgs = [
        {"role": "user",      "content": "What is 2 + 2?"},
        {"role": "assistant", "content": "4"},
        {"role": "user",      "content": "And 4 + 4?"},
    ]
    t0 = time.perf_counter()
    result = client.chat(system_prompt=SYS, messages=msgs, max_tokens=32)
    elapsed = time.perf_counter() - t0
    print(f"   Response ({elapsed:.2f}s): {result!r}")
    print("")

    print(SEP)
    print("  All tests passed [PASS]")
    print(SEP)
    print("")
