"""
Auth middleware — protected vs unprotected routes, JWT-based.

@require_client — any valid JWT (role client or admin); g.client_id = sub.
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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def _bearer():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.headers.get("x-token")


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
        g.client_id = claims["sub"]
        g.role = claims.get("role", "client")
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
