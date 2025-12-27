import os
import httpx
import jwt
from jwt import PyJWKClient
from fastapi import APIRouter, HTTPException, Request
from .models import AuthorizeRequest, AuthorizeResponse

AUTH0_CLIENT_ID = os.environ["AUTH0_CLIENT_ID"]
AUTH0_CLIENT_SECRET = os.environ["AUTH0_CLIENT_SECRET"]
AUTH0_DOMAIN = os.environ["AUTH0_DOMAIN"]

AUTH0_TOKEN_URL = f"https://{AUTH0_DOMAIN}/oauth/token"
AUTH0_SCOPE = "openid profile email"

AUTH0_ISSUER = os.environ["AUTH0_ISSUER"]
AUTH0_JWKS_URI = os.environ["AUTH0_JWKS_URI"]

AUTH0_AUDIENCE = os.environ["AUTH0_AUDIENCE"]

jwk_client = PyJWKClient(AUTH0_JWKS_URI)

router = APIRouter()


@router.post("/api/v1/authorize", response_model=AuthorizeResponse)
async def authorize(payload: AuthorizeRequest):
    body = {
        "grant_type": "password",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "username": payload.username,
        "password": payload.password,
        "scope": AUTH0_SCOPE,
        "audience": AUTH0_AUDIENCE,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.post(
                AUTH0_TOKEN_URL,
                json=body,
                headers={"content-type": "application/json"})
            r.raise_for_status()
        except httpx.HTTPStatusError:
            raise HTTPException(status_code=401, detail="Некорректная авторизация")

    data = r.json()
    return AuthorizeResponse(
        access_token=data["access_token"],
        token_type=data.get("token_type", "Bearer"),
        expires_in=data.get("expires_in", 0))


def verify_jwt(request: Request) -> dict:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Некорректная авторизация")

    token = auth.split(" ", 1)[1].strip()

    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=AUTH0_ISSUER,
            options={"require": ["exp", "iss"], "verify_aud": False},
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Некорректная авторизация")

    request.state.claims = claims
    return claims


def username_from_claims(claims: dict) -> str:
    username = claims.get("sub")
    return username


@router.post("/oauth/token")
async def oauth_token(request: Request):
    ctype = (request.headers.get("content-type") or "").lower()

    if "application/json" in ctype:
        payload = await request.json()
    else:
        form = await request.form()
        payload = dict(form)

    if "clientId" in payload and "client_id" not in payload:
        payload["client_id"] = payload.pop("clientId")
    if "clientSecret" in payload and "client_secret" not in payload:
        payload["client_secret"] = payload.pop("clientSecret")

    payload.setdefault("grant_type", "password")
    payload.setdefault("client_id", AUTH0_CLIENT_ID)
    payload.setdefault("client_secret", AUTH0_CLIENT_SECRET)
    payload.setdefault("scope", AUTH0_SCOPE)

    if AUTH0_AUDIENCE:
        payload.setdefault("audience", AUTH0_AUDIENCE)

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.post(
                AUTH0_TOKEN_URL,
                data=payload,
                headers={"content-type": "application/x-www-form-urlencoded"},
            )
            r.raise_for_status()
        except httpx.HTTPStatusError:
            raise HTTPException(status_code=401, detail="Некорректная авторизация")

    return r.json()
