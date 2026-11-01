# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Zero-dependency, RFC 7519 compliant JSON Web Token (JWT) engine with HS256 support."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


class JWTError(Exception):
    """Base exception for JWT encoding/decoding errors."""


class ExpiredSignatureError(JWTError):
    """Raised when a token has passed its expiration time (exp claim)."""


class InvalidTokenError(JWTError):
    """Raised when a token signature is invalid, malformed, or claims mismatch."""


def b64url_encode(data: bytes) -> str:
    """Encode bytes into base64url string without trailing padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    """Decode base64url string into bytes, restoring required padding."""
    pad = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("ascii"))


def generate_jwt(
    payload: dict[str, Any],
    secret: str,
    algorithm: str = "HS256",
    expires_in_seconds: int | None = 86400,
) -> str:
    """Generate and sign an RFC 7519 JSON Web Token with HMAC-SHA256.

    Args:
        payload: Dictionary of claims to include (e.g. sub, role, iss).
        secret: HMAC secret key used for signing.
        algorithm: Signing algorithm (must be HS256).
        expires_in_seconds: Seconds until expiration (sets 'exp' claim).
    """
    if algorithm != "HS256":
        raise ValueError(f"Unsupported algorithm '{algorithm}'; only 'HS256' is supported.")
    if not secret:
        raise ValueError("Secret key cannot be empty.")

    now = int(time.time())
    token_claims = dict(payload)
    token_claims.setdefault("iat", now)
    if expires_in_seconds is not None and "exp" not in token_claims:
        token_claims["exp"] = now + expires_in_seconds

    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_json = json.dumps(token_claims, separators=(",", ":"), sort_keys=True).encode("utf-8")

    header_b64 = b64url_encode(header_json)
    payload_b64 = b64url_encode(payload_json)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_and_verify_jwt(
    token: str,
    secret: str,
    allowed_algorithms: tuple[str, ...] = ("HS256",),
    issuer: str | None = None,
    audience: str | None = None,
    leeway_seconds: int = 60,
) -> dict[str, Any]:
    """Cryptographically verify and decode a JWT.

    Args:
        token: Raw JWT string (header.payload.signature).
        secret: HMAC secret key.
        allowed_algorithms: Permitted algorithms (default: ('HS256',)).
        issuer: Expected issuer claim (iss) if enforced.
        audience: Expected audience claim (aud) if enforced.
        leeway_seconds: Clock skew margin in seconds.

    Returns:
        The validated dictionary of claims.

    Raises:
        InvalidTokenError: If malformed, untrusted alg, or signature mismatch.
        ExpiredSignatureError: If token expiration (exp) is in the past.
    """
    clean_token = token.strip()
    parts = clean_token.split(".")
    if len(parts) != 3:
        raise InvalidTokenError(
            "Malformed JWT: token must contain exactly three dot-separated segments."
        )

    header_b64, payload_b64, signature_b64 = parts

    try:
        header_raw = b64url_decode(header_b64)
        header = json.loads(header_raw.decode("utf-8"))
    except Exception as exc:
        raise InvalidTokenError(f"Malformed JWT header: {exc}") from exc

    alg = header.get("alg")
    if alg not in allowed_algorithms or alg == "none":
        raise InvalidTokenError(f"Unsupported algorithm '{alg}'. Permitted: {allowed_algorithms}")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()

    try:
        provided_sig = b64url_decode(signature_b64)
    except Exception as exc:
        raise InvalidTokenError(f"Malformed signature encoding: {exc}") from exc

    if not hmac.compare_digest(provided_sig, expected_sig):
        raise InvalidTokenError("Signature verification failed: invalid HMAC signature.")

    try:
        payload_raw = b64url_decode(payload_b64)
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception as exc:
        raise InvalidTokenError(f"Malformed JWT payload: {exc}") from exc

    now = int(time.time())

    # Check expiration (exp)
    if "exp" in payload:
        try:
            exp = int(payload["exp"])
        except (ValueError, TypeError) as exc:
            raise InvalidTokenError("Invalid 'exp' claim in JWT.") from exc
        if exp < (now - leeway_seconds):
            raise ExpiredSignatureError(f"Token has expired (exp: {exp}, now: {now}).")

    # Check not-before (nbf)
    if "nbf" in payload:
        try:
            nbf = int(payload["nbf"])
        except (ValueError, TypeError) as exc:
            raise InvalidTokenError("Invalid 'nbf' claim in JWT.") from exc
        if nbf > (now + leeway_seconds):
            raise InvalidTokenError(f"Token not yet valid (nbf: {nbf}, now: {now}).")

    # Check issuer (iss)
    if issuer and payload.get("iss") != issuer:
        raise InvalidTokenError(f"Invalid issuer: expected '{issuer}', got '{payload.get('iss')}'.")

    # Check audience (aud)
    if audience and payload.get("aud") != audience:
        raise InvalidTokenError(
            f"Invalid audience: expected '{audience}', got '{payload.get('aud')}'."
        )

    return payload
