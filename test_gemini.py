import os
import sys
from google import genai
from dotenv import load_dotenv

load_dotenv()

def test_gemini_minimal():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment")
        return

    print(f"Checking Gemini with key: {api_key[:5]}...{api_key[-4:]}")
    client = genai.Client(api_key=api_key)
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Hi, say 'READY' if you are working."
        )
        print(f"✅ Response: {response.text}")
    except Exception as e:
        print(f"❌ Gemini Error: {e}")

if __name__ == "__main__":
    test_gemini_minimal()
