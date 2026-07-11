import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

def test_gemini(api_key, model=None):
    try:
        from google import genai
    except ImportError:
        raise ImportError("google-genai package is not installed. Run 'pip install google-genai'")
    
    model = model or "gemini-2.5-flash"
    print(f"Testing Gemini ({model}) using key: {api_key[:5]}...{api_key[-4:]}")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents="Hi, say 'READY'."
    )
    return response.text.strip()

def test_openai(api_key, model=None):
    try:
        import openai
    except ImportError:
        raise ImportError("openai package is not installed. Run 'pip install openai'")
        
    model = model or "gpt-4o-mini"
    print(f"Testing OpenAI ({model}) using key: {api_key[:5]}...{api_key[-4:]}")
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Hi, say 'READY'."}],
        max_tokens=10
    )
    return response.choices[0].message.content.strip()

def test_anthropic(api_key, model=None):
    try:
        from anthropic import Anthropic
    except ImportError:
        raise ImportError("anthropic package is not installed. Run 'pip install anthropic'")
        
    model = model or "claude-3-5-sonnet-20241022"
    print(f"Testing Anthropic ({model}) using key: {api_key[:10]}...")
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=100,
        messages=[{"role": "user", "content": "Hi, say 'READY'."}]
    )
    return message.content[0].text.strip()

def test_deepseek(api_key, model=None):
    try:
        import openai
    except ImportError:
        raise ImportError("openai package is not installed. Run 'pip install openai'")
        
    model = model or "deepseek-chat"
    print(f"Testing DeepSeek ({model}) using key: {api_key[:5]}...{api_key[-4:]}")
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Hi, say 'READY'."}],
        max_tokens=10
    )
    return response.choices[0].message.content.strip()

# Map providers to keys, test functions, and default models
PROVIDERS = {
    "gemini": {
        "env_var": "GEMINI_API_KEY",
        "test_func": test_gemini,
        "default_model": "gemini-2.5-flash"
    },
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "test_func": test_openai,
        "default_model": "gpt-4o-mini"
    },
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
        "test_func": test_anthropic,
        "default_model": "claude-3-5-sonnet-20241022"
    },
    "deepseek": {
        "env_var": "DEEPSEEK_API_KEY",
        "test_func": test_deepseek,
        "default_model": "deepseek-chat"
    }
}

def main():
    parser = argparse.ArgumentParser(description="Test LLM provider connectivity.")
    parser.add_argument("--provider", choices=list(PROVIDERS.keys()), help="LLM Provider to test")
    parser.add_argument("--model", help="Specific model to test")
    args = parser.parse_args()
    
    if args.provider:
        prov_info = PROVIDERS[args.provider]
        api_key = os.getenv(prov_info["env_var"])
        if not api_key:
            print(f"Error: Environment variable {prov_info['env_var']} not found.")
            sys.exit(1)
        try:
            res = prov_info["test_func"](api_key, args.model)
            print(f"Success! Response: {res}")
        except Exception as e:
            print(f"Failed: {e}")
            sys.exit(1)
    else:
        print("No provider specified. Scanning environment for keys...\n")
        active_any = False
        for name, info in PROVIDERS.items():
            api_key = os.getenv(info["env_var"])
            if api_key:
                active_any = True
                print("-" * 50)
                try:
                    res = info["test_func"](api_key)
                    print(f"Success! Response: {res}")
                except Exception as e:
                    print(f"Failed: {e}")
        print("-" * 50)
        if not active_any:
            print("No API keys found in environment variables (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY).")

if __name__ == "__main__":
    main()

    # Reference: https://aistudio.google.com/
    # Powershell
    # python test_gemini.py
    # python test_gemini.py --provider deepseek
    # python test_gemini.py --provider anthropic
    # python test_gemini.py --provider gemini --model gemini-2.5-flash
    # python test_gemini.py --provider gemini --model gemini-3.1-flash-lite

