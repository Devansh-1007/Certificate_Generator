"""
JWT issue/verify — replaces the AES-CBC token scheme.

Tokens are HS256-signed with JWT_SECRET and carry:
    sub  — client id
    name — client name
    role — "client" | "admin"
    iat / exp — issued-at / expiry (default 12h)

Why JWT over the old scheme: signed (tamper-evident) instead of encrypted,
carries an expiry so tokens rotate, and embeds a role so admin is a real
authenticated identity instead of a static string.
"""

import os
import logging
import datetime

import jwt as pyjwt

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

ALGORITHM = "HS256"
DEFAULT_TTL_HOURS = 12


def _secret():
    secret = os.getenv("JWT_SECRET")
    if not secret:
        logging.warning("JWT_SECRET not set — using insecure dev secret")
        secret = "dev-secret-change-me"
    return secret


def issue_token(sub, name="", role="client", ttl_hours=DEFAULT_TTL_HOURS):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": sub,
        "name": name,
        "role": role,
        "iat": now,
        "exp": now + datetime.timedelta(hours=ttl_hours),
    }
    return pyjwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token):
    """Returns the claims dict. Raises pyjwt.InvalidTokenError (incl. expiry) on failure."""
    return pyjwt.decode(token, _secret(), algorithms=[ALGORITHM])
