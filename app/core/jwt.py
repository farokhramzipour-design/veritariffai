import base64
import json
import time
import hmac
import hashlib
from typing import Any, Dict, Optional
from app.config import settings


def _b64url_decode(data: str) -> bytes:
    rem = len(data) % 4
    if rem:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode())


def _decode_segments(token: str) -> tuple[dict, dict, bytes]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid token")
    header = json.loads(_b64url_decode(parts[0]).decode())
    payload = json.loads(_b64url_decode(parts[1]).decode())
    signature = _b64url_decode(parts[2])
    return header, payload, signature


def _verify_hs256(token: str, secret: str) -> dict:
    header_b64, payload_b64, sig_b64 = token.split(".")
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    actual = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected, actual):
        raise ValueError("invalid signature")
    payload = json.loads(_b64url_decode(payload_b64).decode())
    return payload


def verify_jwt(token: str) -> dict:
    header, payload, _ = _decode_segments(token)
    alg = header.get("alg", settings.jwt_algorithm)
    if alg == "HS256":
        claims = _verify_hs256(token, settings.secret_key)
    else:
        kid = header.get("kid")
        if not kid or kid not in settings.jwt_public_keys:
            raise ValueError("public key not found")
        raise NotImplementedError("RS256 verification requires crypto library")
    now = int(time.time())
    if "exp" in claims and int(claims["exp"]) < now:
        raise ValueError("token expired")
    if settings.jwt_issuer and claims.get("iss") != settings.jwt_issuer:
        raise ValueError("invalid issuer")
    if settings.jwt_audience and claims.get("aud") != settings.jwt_audience:
        raise ValueError("invalid audience")
    return claims

