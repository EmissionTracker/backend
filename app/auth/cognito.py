import urllib.request
import json
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

bearer_scheme = HTTPBearer()


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    with urllib.request.urlopen(settings.cognito_jwks_url) as response:
        return json.loads(response.read())


def _get_public_key(token: str) -> str:
    header = jwt.get_unverified_header(token)
    jwks = _get_jwks()
    for key in jwks["keys"]:
        if key["kid"] == header["kid"]:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Public key not found")


def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> dict:
    token = credentials.credentials
    try:
        public_key = _get_public_key(token)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


CurrentUser = Annotated[dict, Depends(verify_token)]
