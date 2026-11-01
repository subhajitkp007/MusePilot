# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Security package: JWT token authentication, rate limiting, and access control."""

from __future__ import annotations

from musepilot.security.jwt import (
    ExpiredSignatureError,
    InvalidTokenError,
    JWTError,
    decode_and_verify_jwt,
    generate_jwt,
)
from musepilot.security.rate_limiter import (
    GLOBAL_RATE_LIMITER,
    RateLimitMiddleware,
    SlidingWindowRateLimiter,
)

__all__ = [
    "ExpiredSignatureError",
    "GLOBAL_RATE_LIMITER",
    "InvalidTokenError",
    "JWTError",
    "RateLimitMiddleware",
    "SlidingWindowRateLimiter",
    "decode_and_verify_jwt",
    "generate_jwt",
]
