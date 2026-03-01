import redis
import os
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
print(f"Checking Redis connection at: {redis_url}")

try:
    r = redis.from_url(redis_url)
    r.ping()
    print("✅ Successfully connected to Redis!")
except Exception as e:
    print(f"❌ Failed to connect to Redis: {e}")
    print("\nPRO TIP: If you don't have Redis installed, you can:")
    print("1. Install Memurai (Redis for Windows)")
    print("2. Run 'docker run -d -p 6379:6379 redis' (if Docker is installed)")
    print("3. Use a free cloud Redis URL (like Upstash)")
