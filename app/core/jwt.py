import base64
import json
import time
import hmac
import hashlib
from typing import Any, Dict, Optional
from app.config import settings


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    rem = len(data) % 4
    if rem:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode())


def create_jwt(payload: dict, secret: str = settings.secret_key, algorithm: str = "HS256") -> str:
    header = {"typ": "JWT", "alg": algorithm}
    header_json = json.dumps(header).encode("utf-8")
    payload_json = json.dumps(payload).encode("utf-8")
    
    header_b64 = _b64url_encode(header_json)
    payload_b64 = _b64url_encode(payload_json)
    
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    
    if algorithm == "HS256":
        signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        sig_b64 = _b64url_encode(signature)
    else:
        raise NotImplementedError("Only HS256 is supported for signing")
        
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _decode_segments(token: str) -> tuple[dict, dict, bytes]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid token")
    header = json.loads(_b64url_decode(parts[0]).decode())
    payload = json.loads(_b64url_decode(parts[1]).decode())
    signature = _b64url_decode(parts[2])
    return header, payload, signature


def _verify_hs256(token: str, secret: str) -> dict:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        actual = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected, actual):
            raise ValueError("invalid signature")
        payload = json.loads(_b64url_decode(payload_b64).decode())
        return payload
    except Exception:
        raise ValueError("invalid token format")


def verify_jwt(token: str) -> dict:
    try:
        header, payload, _ = _decode_segments(token)
    except Exception:
        raise ValueError("invalid token format")
        
    alg = header.get("alg", settings.jwt_algorithm)
    
    # For now, we only support HS256 for our own tokens
    # If you want to support RS256 (e.g. from Auth0 or Google directly), you need a library like python-jose
    if alg == "HS256":
        claims = _verify_hs256(token, settings.secret_key)
    else:
        # If the token is not HS256, we can't verify it with our secret key
        # This might happen if you are trying to verify a Google ID token as an access token
        raise ValueError(f"Unsupported algorithm: {alg}")

    now = int(time.time())
    if "exp" in claims and int(claims["exp"]) < now:
        raise ValueError("token expired")
    if settings.jwt_issuer and claims.get("iss") != settings.jwt_issuer:
        raise ValueError("invalid issuer")
    if settings.jwt_audience and claims.get("aud") != settings.jwt_audience:
        raise ValueError("invalid audience")
    return claims
