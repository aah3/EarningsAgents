import os
import requests
from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient, PyJWTError

# You'll need to set these in your .env file
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL") or "https://clerk.example.com/.well-known/jwks.json"
CLERK_API_URL = os.getenv("CLERK_API_URL") or "https://api.clerk.dev/v1"

# Initialize PyJWKClient. This automatically fetches and caches JWKS.
jwks_client = PyJWKClient(CLERK_JWKS_URL)

security = HTTPBearer()


def resolve_user_id_from_token(token: str) -> str:
    """
    Resolve a bearer token to a Clerk user id, verifying a real Clerk JWT.
    Shared by get_current_user (auth) and the rate-limit key function so both
    use the exact same identity resolution / dev bypass rules.

    Raises PyJWTError subclasses or HTTPException on failure - callers that
    just want a best-effort identity (e.g. rate limiting) should catch
    broadly and fall back to another key (e.g. remote IP).
    """
    # Dev-only bypass: lets local scripts/tests call the API without a real
    # Clerk JWT. Gated on ENV=dev so it can never fire in staging/production
    # even if a caller sends a mock_/test_-prefixed bearer token.
    if os.getenv("ENV") == "dev" and (token.startswith("mock_") or token.startswith("test_")):
        return token

    # Get the signing key from the JWT
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    # Verify the JWT
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        # You should also verify audience (azp) and issuer (iss) in production
        options={"verify_aud": False, "verify_iat": False},
        leeway=60  # Add 60 seconds of leeway for clock skew
    )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user identity")

    return user_id


def get_current_user(auth: HTTPAuthorizationCredentials = Security(security)):
    """
    FastAPI dependency to verify a Clerk JWT.
    Returns the Clerk user_id if valid.
    """
    token = auth.credentials
    try:
        return resolve_user_id_from_token(token)
    except HTTPException:
        raise
    except PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")
