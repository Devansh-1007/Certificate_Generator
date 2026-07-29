"""
Tenant auth and organisation management.

POST /auth/signup           public — create an organisation + its owner
POST /auth/login            public — email + password -> org-scoped JWT
GET  /auth/me               current user, organisation and usage
GET  /auth/organisation     org profile (name, slug, plan, branding)
PATCH /auth/organisation    owner/admin — rename, set brand colour/logo
GET  /auth/members          list teammates
POST /auth/members          owner/admin — add a teammate
PATCH /auth/members/<id>    owner/admin — change role or suspend

Anyone signed in can issue certificates; roles only gate org administration.
That is the difference from the old model, where the sole admin could manage
accounts but not use the product.
"""

import logging

from flask import Blueprint, request, jsonify, g

import tenancy
import oauth_google
from tenancy import TenancyError
from auth_jwt import issue_token
from middleware import require_member

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

auth_bp = Blueprint("auth", __name__)


def _token_for(user):
    """One place that decides what a session token carries."""
    return issue_token(
        user["USER_ID"],
        name=user.get("FULL_NAME") or user["EMAIL"],
        role=user["ROLE"],
        org=user["ORG_ID"],
        org_name=user.get("ORG_NAME"),
        org_slug=user.get("ORG_SLUG"),
        plan=user.get("PLAN"),
        email=user["EMAIL"],
    )


def _session_payload(user):
    return {
        "access_token": _token_for(user),
        "USER": {
            "USER_ID": user["USER_ID"], "EMAIL": user["EMAIL"],
            "FULL_NAME": user.get("FULL_NAME"), "ROLE": user["ROLE"],
        },
        "ORGANISATION": {
            "ORG_ID": user["ORG_ID"], "NAME": user.get("ORG_NAME"),
            "SLUG": user.get("ORG_SLUG"), "PLAN": user.get("PLAN", "free"),
        },
    }


@auth_bp.route("/auth/config", methods=["GET"])
def config():
    """Public: lets the sign-in page render the right options for this deployment."""
    problem = oauth_google.config_problem()
    return jsonify({
        "GOOGLE_ENABLED": problem is None,
        "GOOGLE_CLIENT_ID": oauth_google.client_id() if problem is None else "",
        "GOOGLE_PROBLEM": problem,
        "REQUIRE_WORK_EMAIL": tenancy.work_email_required(),
    })


@auth_bp.route("/auth/google", methods=["POST"])
def google_signin():
    """
    Exchange a Google ID token for a session. One endpoint covers sign-up and
    sign-in: the outcome tells the client what happened so the UI can explain
    it ("joined Acme Inc" vs "created Acme Inc").
    """
    data = request.get_json() or {}
    try:
        identity = oauth_google.verify_id_token(data.get("CREDENTIAL"))
    except oauth_google.GoogleAuthError as e:
        return jsonify({"description": str(e)}), 401

    try:
        user, outcome = tenancy.sign_in_with_google(identity, org_name=data.get("ORG_NAME"))
    except TenancyError as e:
        return jsonify({"description": str(e)}), 400
    except Exception as e:  # noqa: BLE001
        logging.error("Google sign-in failed for %s: %s", identity.get("email"), e)
        return jsonify({"description": "Could not complete Google sign-in."}), 503

    payload = _session_payload(user)
    payload["OUTCOME"] = outcome
    return jsonify(payload), (201 if outcome == "created" else 200)


@auth_bp.route("/auth/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}
    try:
        user = tenancy.create_organisation(
            org_name=data.get("ORG_NAME", ""),
            email=data.get("EMAIL", ""),
            password=data.get("PASSWORD", ""),
            full_name=data.get("FULL_NAME"),
        )
    except TenancyError as e:
        return jsonify({"description": str(e)}), 400
    except Exception as e:  # noqa: BLE001
        logging.error("Signup failed: %s", e)
        return jsonify({"description": "Could not create the account right now."}), 503
    return jsonify(_session_payload(user)), 201


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    try:
        user = tenancy.authenticate(data.get("EMAIL", ""), data.get("PASSWORD", ""))
    except TenancyError as e:
        return jsonify({"description": str(e)}), 403
    except Exception as e:  # noqa: BLE001
        logging.error("Login failed: %s", e)
        return jsonify({"description": "Sign-in is unavailable right now."}), 503
    if not user:
        # Deliberately identical for unknown email and wrong password.
        return jsonify({"description": "Incorrect email or password."}), 401
    return jsonify(_session_payload(user))


@auth_bp.route("/auth/me", methods=["GET"])
@require_member()
def me():
    org = tenancy.get_organisation(g.org_id)
    return jsonify({
        "USER": {"USER_ID": g.user_id, "EMAIL": g.email, "ROLE": g.role},
        "ORGANISATION": org,
        "USAGE": tenancy.org_usage(g.org_id),
    })


@auth_bp.route("/auth/organisation", methods=["GET"])
@require_member()
def organisation():
    org = tenancy.get_organisation(g.org_id)
    if not org:
        return jsonify({"description": "Organisation not found."}), 404
    return jsonify({"ORGANISATION": org, "USAGE": tenancy.org_usage(g.org_id)})


@auth_bp.route("/auth/organisation", methods=["PATCH"])
@require_member("admin")
def update_organisation():
    data = request.get_json() or {}
    try:
        org = tenancy.update_organisation(
            g.org_id,
            name=data.get("NAME"),
            brand_color=data.get("BRAND_COLOR"),
            logo_url=data.get("LOGO_URL"),
        )
    except TenancyError as e:
        return jsonify({"description": str(e)}), 400
    return jsonify({"ORGANISATION": org})


@auth_bp.route("/auth/members", methods=["GET"])
@require_member()
def members():
    return jsonify({"MEMBERS": tenancy.list_members(g.org_id)})


@auth_bp.route("/auth/members", methods=["POST"])
@require_member("admin")
def add_member():
    data = request.get_json() or {}
    try:
        created = tenancy.invite_member(
            g.org_id,
            email=data.get("EMAIL", ""),
            password=data.get("PASSWORD", ""),
            role=data.get("ROLE", "member"),
            full_name=data.get("FULL_NAME"),
        )
    except TenancyError as e:
        return jsonify({"description": str(e)}), 400
    return jsonify({"MEMBER": created}), 201


@auth_bp.route("/auth/members/<user_id>", methods=["PATCH"])
@require_member("admin")
def patch_member(user_id):
    data = request.get_json() or {}
    try:
        tenancy.update_member(g.org_id, user_id, role=data.get("ROLE"), status=data.get("STATUS"))
    except TenancyError as e:
        return jsonify({"description": str(e)}), 400
    return jsonify({"MEMBERS": tenancy.list_members(g.org_id)})
