"""
Google Sign-In verification.

The browser runs Google Identity Services and hands us an **ID token** (a JWT
signed by Google). We verify it server-side rather than trusting anything the
page sends: signature against Google's published keys, issuer, audience (our
client id) and expiry. Only then do we believe the email inside it.

No new dependency: PyJWT (already used for our own sessions) ships PyJWKClient,
and `cryptography` — needed for RS256 — is already in requirements.
"""

import os
import logging

import jwt as pyjwt
from jwt import PyJWKClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"

# Keys are cached and rotated by the client, so this is created once.
_jwk_client = None


class GoogleAuthError(Exception):
    """The ID token could not be trusted; the message is safe to show a user."""


def is_configured():
    return bool(os.getenv("GOOGLE_CLIENT_ID"))


def client_id():
    return os.getenv("GOOGLE_CLIENT_ID", "")


def _jwks():
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(GOOGLE_JWKS_URL, cache_keys=True)
    return _jwk_client


def verify_id_token(id_token):
    """
    Validate a Google ID token and return the identity it asserts:
    {sub, email, email_verified, name, picture, hd}

    `hd` is the Google Workspace hosted domain — present only for Workspace
    accounts, and a stronger signal of org membership than the email suffix.
    """
    if not is_configured():
        raise GoogleAuthError("Google sign-in is not configured on this server.")
    if not id_token:
        raise GoogleAuthError("Missing Google credential.")

    try:
        signing_key = _jwks().get_signing_key_from_jwt(id_token)
        claims = pyjwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id(),
            options={"require": ["exp", "iat", "aud", "iss", "sub"]},
        )
    except pyjwt.ExpiredSignatureError:
        raise GoogleAuthError("That Google sign-in expired. Try again.")
    except pyjwt.InvalidAudienceError:
        raise GoogleAuthError("This Google credential was issued for a different app.")
    except Exception as e:  # noqa: BLE001 - any verification failure is a rejection
        logging.warning("Google ID token rejected: %s", e)
        raise GoogleAuthError("Could not verify that Google account.")

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise GoogleAuthError("Unexpected token issuer.")

    email = (claims.get("email") or "").strip().lower()
    if not email:
        raise GoogleAuthError("That Google account has no email address.")
    if not claims.get("email_verified", False):
        raise GoogleAuthError("Verify your email with Google before signing in.")

    return {
        "sub": claims["sub"],
        "email": email,
        "email_verified": True,
        "name": claims.get("name") or "",
        "picture": claims.get("picture"),
        "hd": (claims.get("hd") or "").lower() or None,
    }
