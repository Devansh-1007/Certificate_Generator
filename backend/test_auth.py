"""JWT auth tests — no DB needed."""
import time
import pytest
import jwt as pyjwt
from auth_jwt import issue_token, decode_token


def test_round_trip():
    t = issue_token("devansh", "Devansh", role="client")
    claims = decode_token(t)
    assert claims["sub"] == "devansh" and claims["role"] == "client"


def test_expired_token_rejected():
    t = issue_token("devansh", ttl_hours=-1)
    with pytest.raises(pyjwt.ExpiredSignatureError):
        decode_token(t)


def test_tampered_token_rejected():
    t = issue_token("devansh")
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_token(t[:-2] + "xx")


def test_middleware_roles():
    from flask import Flask
    from middleware import require_client, require_admin

    app = Flask(__name__)

    @app.route("/c")
    @require_client
    def c(): return "ok"

    @app.route("/a")
    @require_admin
    def a(): return "ok"

    client_tok = issue_token("dev", role="client")
    admin_tok = issue_token("boss", role="admin")
    with app.test_client() as tc:
        assert tc.get("/c").status_code == 401
        assert tc.get("/c", headers={"x-token": client_tok}).status_code == 200
        assert tc.get("/c", headers={"Authorization": "Bearer " + client_tok}).status_code == 200
        assert tc.get("/a", headers={"x-token": client_tok}).status_code == 401
        assert tc.get("/a", headers={"x-token": admin_tok}).status_code == 200
        # admins are not clients: clear 403 instead of a DB foreign-key error
        assert tc.get("/c", headers={"x-token": admin_tok}).status_code == 403
