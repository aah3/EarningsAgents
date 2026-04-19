import os
import logging
import time
from typing import Optional, List, Any

# Configure logging
logger = logging.getLogger(__name__)

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
                self.model = self.model or "gemini-2.5-flash" 
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

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 2048, on_retry=None, **kwargs) -> str:
        """
        Generates content from the LLM based on system and user prompts.
        Includes basic retry logic for rate limits.
        """
        if not self.client:
            return "⚠️ Error: LLM client not initialized. Check API key and provider settings."

        max_retries = 3
        base_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                # Add a small delay between any calls to avoid instant burst 429s
                if attempt > 0:
                    time.sleep(base_delay * (2 ** (attempt - 1)))
                else:
                    time.sleep(1) # Small initial pause

                if self.provider == "gemini":
                    return self._call_gemini(system_prompt, user_prompt, temperature, max_tokens, **kwargs)
                elif self.provider == "anthropic":
                    return self._call_anthropic(system_prompt, user_prompt, temperature, max_tokens, **kwargs)
                elif self.provider == "openai":
                    return self._call_openai(system_prompt, user_prompt, temperature, max_tokens, **kwargs)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "rate_limit" in err_msg.lower() or "quota" in err_msg.lower():
                    logger.warning(f"Rate limit hit on {self.provider} (attempt {attempt+1}/{max_retries}). Retrying...")
                    if on_retry:
                        on_retry(f"API Rate Limit hit. Retrying attempt {attempt+1} of {max_retries}...")
                    continue
                
                logger.error(f"Error calling {self.provider} API: {e}")
                return f"⚠️ Error: {str(e)}"
        
        return "⚠️ Error: Maximum retries exceeded for LLM call."

    def generate_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 2048, on_retry=None, **kwargs):
        """
        Generates content from the LLM based on system and user prompts, yielding chunks as they arrive.
        """
        if not self.client:
            yield "⚠️ Error: LLM client not initialized."
            return

        max_retries = 3
        base_delay = 5

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(base_delay * (2 ** (attempt - 1)))
                else:
                    time.sleep(1) # Small initial pause

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
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "rate_limit" in err_msg.lower() or "quota" in err_msg.lower():
                    logger.warning(f"Rate limit hit on {self.provider} streaming (attempt {attempt+1}/{max_retries}). Retrying...")
                    if on_retry:
                        on_retry(f"API Rate Limit hit. Retrying attempt {attempt+1} of {max_retries}...")
                    if attempt == max_retries - 1:
                        yield f"\n⚠️ Error: {str(e)}"
                    continue
                
                logger.error(f"Error streaming {self.provider} API: {e}")
                yield f"\n⚠️ Error: {str(e)}"
                break

    def chat(self, system_prompt: str, messages: List[dict], temperature: float = 0.3, max_tokens: int = 2048, on_retry=None) -> str:
        """
        Continues a conversation using a list of messages: [{"role": "user"|"model", "content": "..."}]
        """
        if not self.client:
            return "⚠️ Error: LLM client not initialized."

        max_retries = 3
        base_delay = 5

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(base_delay * (2 ** (attempt - 1)))
                else:
                    time.sleep(1)

                if self.provider == "gemini":
                    return self._chat_gemini(system_prompt, messages, temperature, max_tokens)
                elif self.provider == "anthropic":
                    return self._chat_anthropic(system_prompt, messages, temperature, max_tokens)
                elif self.provider == "openai":
                    return self._chat_openai(system_prompt, messages, temperature, max_tokens)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "rate_limit" in err_msg.lower() or "quota" in err_msg.lower():
                    logger.warning(f"Rate limit hit on {self.provider} (chat attempt {attempt+1}/{max_retries}). Retrying...")
                    if on_retry:
                        on_retry(f"API Rate Limit hit in chat. Retrying attempt {attempt+1} of {max_retries}...")
                    continue
                logger.error(f"Error calling {self.provider} API: {e}")
                return f"⚠️ Error: {str(e)}"
        
        return "⚠️ Error: Maximum retries exceeded for LLM chat."

    def _call_gemini(self, sys_prompt, user_prompt, temperature, max_tokens, **kwargs):
        config = {
            'system_instruction': sys_prompt,
            'temperature': temperature,
            'max_output_tokens': max_tokens
        }
        if "generation_config" in kwargs:
            config.update(kwargs["generation_config"])
            
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=config
        )
        return response.text

    def _call_anthropic(self, sys_prompt, user_prompt, temperature, max_tokens, **kwargs):
        call_kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": sys_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ]
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
        call_kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if "response_format" in kwargs:
            call_kwargs["response_format"] = kwargs["response_format"]
            
        response = self.client.chat.completions.create(**call_kwargs)
        return response.choices[0].message.content

    def _stream_gemini(self, sys_prompt, user_prompt, temperature, max_tokens, **kwargs):
        config = {
            'system_instruction': sys_prompt,
            'temperature': temperature,
            'max_output_tokens': max_tokens
        }
        if "generation_config" in kwargs:
            config.update(kwargs["generation_config"])
            
        response = self.client.models.generate_content_stream(
            model=self.model,
            contents=user_prompt,
            config=config
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text

    def _stream_anthropic(self, sys_prompt, user_prompt, temperature, max_tokens, **kwargs):
        call_kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": sys_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ]
        }
        if "tools" in kwargs:
            call_kwargs["tools"] = kwargs["tools"]
        if "tool_choice" in kwargs:
            call_kwargs["tool_choice"] = kwargs["tool_choice"]
            
        with self.client.messages.stream(**call_kwargs) as stream:
            for text in stream.text_stream:
                if text:
                    yield text

    def _stream_openai(self, sys_prompt, user_prompt, temperature, max_tokens, **kwargs):
        call_kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        if "response_format" in kwargs:
            call_kwargs["response_format"] = kwargs["response_format"]
            
        response = self.client.chat.completions.create(**call_kwargs)
        for chunk in response:
            if getattr(chunk.choices[0].delta, "content", None):
                yield chunk.choices[0].delta.content

    def _chat_gemini(self, sys_prompt, messages, temperature, max_tokens):
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config={
                'system_instruction': sys_prompt,
                'temperature': temperature,
                'max_output_tokens': max_tokens
            }
        )
        return response.text

    def _chat_anthropic(self, sys_prompt, messages, temperature, max_tokens):
        formatted_msgs = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "assistant"
            formatted_msgs.append({"role": role, "content": msg["content"]})
            
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=sys_prompt,
            messages=formatted_msgs
        )
        return message.content[0].text

    def _chat_openai(self, sys_prompt, messages, temperature, max_tokens):
        formatted_msgs = [{"role": "system", "content": sys_prompt}]
        for msg in messages:
            role = "user" if msg["role"] == "user" else "assistant"
            formatted_msgs.append({"role": role, "content": msg["content"]})
            
        response = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_msgs,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
