import os
import time
import httpx
import jwt
from jwt import PyJWKClient
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

AUTH0_ISSUER = os.environ["AUTH0_ISSUER"]
AUTH0_JWKS_URI = os.environ["AUTH0_JWKS_URI"]

jwk_client = PyJWKClient(AUTH0_JWKS_URI)

router = APIRouter()


class AuthorizeRequest(BaseModel):
    username: str
    password: str


class AuthorizeResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


def verify_jwt(request: Request) -> dict:
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Некорректная авторизация")

    token = auth.split(" ", 1)[1].strip()

    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=AUTH0_ISSUER,
            options={
                "require": ["exp", "iss"],
                "verify_aud": False})
    except:
        raise HTTPException(status_code=401, detail="Некорректная авторизация")

    request.state.claims = claims
    return claims


def username_from_claims(claims: dict) -> str:
    return claims.get("sub")
