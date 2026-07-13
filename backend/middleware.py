"""
Auth middleware — the protected/unprotected route concept.

@require_client  — validates x-client-id / x-token headers (AES token scheme),
                   puts the verified client id on flask.g.client_id.
@require_admin   — validates x-token against the admin token.

Unprotected routes (e.g. /loginClient) simply use no decorator.
"""

import logging
from functools import wraps

from flask import request, jsonify, g

from authentication import verifyToken, verifyAdmin

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def require_client(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        client = request.headers.get("x-client-id")
        token = request.headers.get("x-token")
        if not client or not token or client != verifyToken(client, token):
            logging.info("Token not verified for client '%s'", client)
            return jsonify({"description": "Token not verified"}), 401
        g.client_id = client
        return f(*args, **kwargs)

    return wrapper


def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        ok, error_code = verifyAdmin(request.headers.get("x-token"))
        if not ok or error_code != 200:
            logging.info("Admin role required. Token not verified.")
            return (
                jsonify(description="Admin role required for this request.Token not verified."),
                error_code,
            )
        return f(*args, **kwargs)

    return wrapper
