import os
import requests
from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

# You'll need to set these in your .env file
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL") or "https://clerk.example.com/.well-known/jwks.json"
CLERK_API_URL = os.getenv("CLERK_API_URL") or "https://api.clerk.dev/v1"

security = HTTPBearer()

def get_current_user(auth: HTTPAuthorizationCredentials = Security(security)):
    """
    FastAPI dependency to verify a Clerk JWT.
    Returns the Clerk user_id if valid.
    """
    token = auth.credentials
    try:
        # 1. Fetch the JWKS from Clerk
        # Note: In production, you should cache this JWKS to avoid redundant network calls
        jwks = requests.get(CLERK_JWKS_URL).json()
        
        # 2. Get the unverified header to find the kid (Key ID)
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(status_code=401, detail="Invalid token header: missing kid")

        # 3. Find the matching key in the JWKS
        key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if not key:
            raise HTTPException(status_code=401, detail="Invalid token: kid not found in JWKS")

        # 4. Verify the JWT
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            # You should also verify audience (azp) and issuer (iss) in production
            options={"verify_aud": False} 
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token missing user identity")
            
        return user_id

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")
