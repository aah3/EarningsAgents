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

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 2048) -> str:
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
                    return self._call_gemini(system_prompt, user_prompt, temperature, max_tokens)
                elif self.provider == "anthropic":
                    return self._call_anthropic(system_prompt, user_prompt, temperature, max_tokens)
                elif self.provider == "openai":
                    return self._call_openai(system_prompt, user_prompt, temperature, max_tokens)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "rate_limit" in err_msg.lower():
                    logger.warning(f"Rate limit hit on {self.provider} (attempt {attempt+1}/{max_retries}). Retrying...")
                    continue
                
                logger.error(f"Error calling {self.provider} API: {e}")
                return f"⚠️ Error: {str(e)}"
        
        return "⚠️ Error: Maximum retries exceeded for LLM call."

    def _call_gemini(self, sys_prompt, user_prompt, temperature, max_tokens):
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config={
                'system_instruction': sys_prompt,
                'temperature': temperature,
                'max_output_tokens': max_tokens
            }
        )
        return response.text

    def _call_anthropic(self, sys_prompt, user_prompt, temperature, max_tokens):
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=sys_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return message.content[0].text

    def _call_openai(self, sys_prompt, user_prompt, temperature, max_tokens):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
