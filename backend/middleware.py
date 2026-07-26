"""
Auth middleware — protected vs unprotected routes, JWT-based.

@require_client — valid JWT with role=client; g.client_id = sub. Admin tokens
                  are rejected with 403: admins manage clients but do not own
                  certificates (CLIENT_ID is a foreign key to CLIENT_DETAILS).
@require_admin  — valid JWT with role=admin, or the bootstrap ADMIN_TOKEN
                  from .env (so the first admin/client can be registered).

Tokens are read from "Authorization: Bearer <jwt>" or the legacy "x-token"
header, so the existing frontend keeps working.
"""

import logging
from functools import wraps

from flask import request, jsonify, g
import jwt as pyjwt

from auth_jwt import decode_token
from config import admin_token
from tenancy import ROLE_RANK

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def _bearer():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.headers.get("x-token")


def _reject(message, code=401):
    return jsonify({"description": message}), code


def _claims_or_error():
    """Decode the bearer token once; returns (claims, error_response)."""
    token = _bearer()
    if not token:
        return None, _reject("Sign in to continue.")
    try:
        return decode_token(token), None
    except pyjwt.ExpiredSignatureError:
        return None, _reject("Session expired — sign in again.")
    except pyjwt.InvalidTokenError:
        return None, _reject("Invalid session token.")


def require_member(minimum="member"):
    """
    Any signed-in member of an organisation. `minimum` raises the bar to
    'admin' or 'owner'. The tenant is taken from the token, never the request,
    so one organisation can't address another's data.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            claims, error = _claims_or_error()
            if error:
                return error
            org_id = claims.get("org")
            if not org_id:
                return _reject(
                    "This account isn't linked to an organisation. Sign in again to refresh it.", 403
                )
            role = claims.get("role", "member")
            if ROLE_RANK.get(role, -1) < ROLE_RANK.get(minimum, 0):
                return _reject("This action needs {} access.".format(minimum), 403)

            g.org_id = org_id
            g.user_id = claims.get("sub")
            g.role = role
            g.email = claims.get("email")
            g.org_name = claims.get("org_name")
            # Legacy handlers still read g.client_id; the organisation is the
            # tenant now, so point it at ORG_ID during the transition.
            g.client_id = org_id
            return f(*args, **kwargs)

        return wrapper

    return decorator


def require_client(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = _bearer()
        if not token:
            return jsonify({"description": "Token not verified"}), 401
        try:
            claims = decode_token(token)
        except pyjwt.ExpiredSignatureError:
            return jsonify({"description": "Token expired — log in again"}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({"description": "Token not verified"}), 401
        if claims.get("role", "client") != "client":
            return (
                jsonify({
                    "description": "Admins manage clients but don't own certificates — "
                                   "sign in with a client account to generate."
                }),
                403,
            )
        g.client_id = claims["sub"]
        g.role = "client"
        return f(*args, **kwargs)

    return wrapper


def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = _bearer()
        # bootstrap: static admin token from .env still accepted
        if token and admin_token and token == admin_token:
            g.client_id, g.role = "admin", "admin"
            return f(*args, **kwargs)
        if token:
            try:
                claims = decode_token(token)
                if claims.get("role") == "admin":
                    g.client_id, g.role = claims["sub"], "admin"
                    return f(*args, **kwargs)
            except pyjwt.InvalidTokenError:
                pass
        logging.info("Admin role required. Token not verified.")
        return (
            jsonify(description="Admin role required for this request.Token not verified."),
            401,
        )

    return wrapper
