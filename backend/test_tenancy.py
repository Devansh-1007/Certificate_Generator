"""
Offline tests for the multi-tenant layer: validation, slugs, token claims and
the role gate. DB-backed functions are exercised through a fake connection so
the suite still needs no MySQL.
"""

import pytest
from flask import Flask, g, jsonify

import tenancy
from tenancy import TenancyError, slugify, validate_signup, ROLE_RANK
from auth_jwt import issue_token
from middleware import require_member


# ---------- validation ----------

def test_slugify_produces_url_safe_names():
    assert slugify("IIT BHU Robotics Club!") == "iit-bhu-robotics-club"
    assert slugify("   ") == "org"


@pytest.mark.parametrize("email", ["nope", "a@b", "@b.com", ""])
def test_signup_rejects_bad_email(email):
    with pytest.raises(TenancyError):
        validate_signup(email, "longenough", "Acme")


def test_signup_rejects_short_password():
    with pytest.raises(TenancyError) as e:
        validate_signup("a@b.com", "short", "Acme")
    assert "8 characters" in str(e.value)


def test_signup_rejects_missing_org_name():
    with pytest.raises(TenancyError):
        validate_signup("a@b.com", "longenough", "")


def test_signup_accepts_valid_input():
    validate_signup("devansh@acme.com", "longenough", "Acme Inc")


# ---------- token claims ----------

def test_token_carries_org_and_role():
    from auth_jwt import decode_token

    token = issue_token("user-1", name="Dev", role="owner", org="org-9", plan="free")
    claims = decode_token(token)
    assert claims["org"] == "org-9" and claims["role"] == "owner" and claims["plan"] == "free"


# ---------- role gate ----------

def _app():
    app = Flask(__name__)

    @app.route("/any")
    @require_member()
    def any_member():
        return jsonify({"org": g.org_id, "role": g.role})

    @app.route("/admin-only")
    @require_member("admin")
    def admin_only():
        return jsonify({"ok": True})

    return app


def test_member_can_use_product_but_not_administer():
    app = _app()
    token = issue_token("u1", role="member", org="org-1")
    with app.test_client() as c:
        assert c.get("/any", headers={"Authorization": "Bearer " + token}).status_code == 200
        # A member is refused administration — and the UI hides it, so this is a backstop.
        assert c.get("/admin-only", headers={"Authorization": "Bearer " + token}).status_code == 403


def test_admin_passes_both_gates():
    app = _app()
    token = issue_token("u2", role="admin", org="org-1")
    with app.test_client() as c:
        assert c.get("/any", headers={"Authorization": "Bearer " + token}).status_code == 200
        assert c.get("/admin-only", headers={"Authorization": "Bearer " + token}).status_code == 200


def test_token_without_org_is_rejected():
    """A legacy token with no tenant must not reach tenant-scoped data."""
    app = _app()
    token = issue_token("u3", role="admin")  # no org claim
    with app.test_client() as c:
        r = c.get("/any", headers={"Authorization": "Bearer " + token})
        assert r.status_code == 403 and "organisation" in r.get_json()["description"]


def test_org_is_taken_from_token_not_request():
    """A caller cannot address another tenant by passing an org in the query."""
    app = _app()
    token = issue_token("u4", role="member", org="org-mine")
    with app.test_client() as c:
        r = c.get("/any?org=org-theirs", headers={"Authorization": "Bearer " + token})
        assert r.get_json()["org"] == "org-mine"


def test_role_rank_ordering():
    assert ROLE_RANK["member"] < ROLE_RANK["admin"] < ROLE_RANK["owner"]


# ---------- last-owner protection ----------

class _FakeCursor:
    def __init__(self, script):
        self.script = script
        self.result = None

    def execute(self, sql, params=()):
        self.result = self.script.pop(0) if self.script else None

    def fetchone(self):
        return self.result

    def close(self):
        pass


class _FakeDB:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def close(self):
        pass


def test_cannot_demote_the_last_owner(monkeypatch):
    # 1st query: the member's role; 2nd: how many active owners remain.
    cur = _FakeCursor([("owner",), (1,)])
    monkeypatch.setattr(tenancy, "configureMySQL", lambda: _FakeDB(cur))
    with pytest.raises(TenancyError) as e:
        tenancy.update_member("org-1", "user-1", role="member")
    assert "at least one active owner" in str(e.value)


def test_can_demote_owner_when_another_exists(monkeypatch):
    cur = _FakeCursor([("owner",), (2,)])
    monkeypatch.setattr(tenancy, "configureMySQL", lambda: _FakeDB(cur))
    assert tenancy.update_member("org-1", "user-1", role="admin") is True


# ---------- work-email policy ----------

from tenancy import is_public_email_domain, email_domain  # noqa: E402


@pytest.mark.parametrize("email", [
    "a@gmail.com", "a@yahoo.co.in", "a@outlook.com", "a@icloud.com", "a@protonmail.com",
])
def test_consumer_domains_are_recognised(email):
    assert is_public_email_domain(email) is True


@pytest.mark.parametrize("email", ["dev@acme.com", "dev@iitbhu.ac.in", "x@sciforn.io"])
def test_work_domains_are_allowed(email):
    assert is_public_email_domain(email) is False


def test_email_domain_extraction():
    assert email_domain("Dev.Choudhary@Acme.COM") == "acme.com"


def test_org_creation_rejects_consumer_email_when_policy_on():
    with pytest.raises(TenancyError) as e:
        validate_signup("someone@gmail.com", "longenough", "Acme", require_work_email=True)
    assert "work email" in str(e.value)


def test_org_creation_allows_consumer_email_when_policy_off():
    validate_signup("someone@gmail.com", "longenough", "Acme", require_work_email=False)


def test_work_email_policy_reads_env(monkeypatch):
    from tenancy import work_email_required

    monkeypatch.delenv("REQUIRE_WORK_EMAIL", raising=False)
    assert work_email_required() is True          # secure default
    monkeypatch.setenv("REQUIRE_WORK_EMAIL", "false")
    assert work_email_required() is False


# ---------- google identity resolution ----------

def test_domain_join_ignores_consumer_domains():
    """Two strangers on gmail.com must never be pooled into one tenant."""
    from tenancy import find_org_for_domain

    class Cur:
        def execute(self, *a, **k):
            raise AssertionError("should not query for a consumer domain")

    assert find_org_for_domain(Cur(), "gmail.com") is None


def test_google_token_verification_requires_configuration(monkeypatch):
    import oauth_google

    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    assert oauth_google.is_configured() is False
    with pytest.raises(oauth_google.GoogleAuthError) as e:
        oauth_google.verify_id_token("anything")
    assert "not configured" in str(e.value)


def test_google_rejects_missing_credential(monkeypatch):
    import oauth_google

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    with pytest.raises(oauth_google.GoogleAuthError):
        oauth_google.verify_id_token("")
