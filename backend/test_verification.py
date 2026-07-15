"""
Offline tests for certificate signing/verification. No DB or network — exercises
the HMAC signing, UID generation, and the tamper/revoke decision logic in
verification.public_result via a monkeypatched get_record.

Run: pytest test_verification.py -v
"""

import verification


def _record(**over):
    r = {
        "CERT_UID": "abc123",
        "CLIENT_ID": "acme.org",
        "RECIPIENT_NAME": "Alice Sharma",
        "EVENT_NAME": "Hackathon 2026",
        "ISSUE_DATE": "15 July 2026",
        "STATUS": "VALID",
        "CREATED_ON": "2026-07-15 10:00:00",
    }
    r.update(over)
    r.setdefault("SIGNATURE", verification.sign(
        r["CERT_UID"], r["CLIENT_ID"], r["RECIPIENT_NAME"], r["EVENT_NAME"], r["ISSUE_DATE"]))
    return r


def test_uid_is_unguessable_and_unique():
    uids = {verification.new_uid() for _ in range(200)}
    assert len(uids) == 200
    assert all(len(u) >= 10 for u in uids)


def test_sign_is_deterministic_and_field_sensitive():
    a = verification.sign("u", "c", "Alice", "Expo", "2026")
    assert a == verification.sign("u", "c", "Alice", "Expo", "2026")
    assert a != verification.sign("u", "c", "Alice", "Expo", "2027")  # date change
    assert a != verification.sign("u", "c", "Bob", "Expo", "2026")    # name change


def test_verify_signature_true_for_intact_record():
    assert verification.verify_signature(_record()) is True


def test_verify_signature_false_when_field_tampered():
    rec = _record()
    rec["RECIPIENT_NAME"] = "Mallory"  # signature no longer matches
    assert verification.verify_signature(rec) is False


def test_public_result_genuine(monkeypatch):
    monkeypatch.setattr(verification, "get_record", lambda uid: _record(CERT_UID=uid))
    res = verification.public_result("abc123")
    assert res["valid"] is True
    assert res["recipient"] == "Alice Sharma"
    assert res["uid"] == "abc123"


def test_public_result_not_found(monkeypatch):
    monkeypatch.setattr(verification, "get_record", lambda uid: None)
    res = verification.public_result("missing")
    assert res == {"valid": False, "reason": "not_found"}


def test_public_result_tampered(monkeypatch):
    bad = _record()
    bad["EVENT_NAME"] = "Forged Award"  # keep old signature -> mismatch
    monkeypatch.setattr(verification, "get_record", lambda uid: bad)
    res = verification.public_result("abc123")
    assert res["valid"] is False
    assert res["reason"] == "tampered"
    assert res["recipient"] == "Alice Sharma"  # details still returned


def test_public_result_revoked(monkeypatch):
    monkeypatch.setattr(verification, "get_record", lambda uid: _record(STATUS="REVOKED"))
    res = verification.public_result("abc123")
    assert res["valid"] is False
    assert res["reason"] == "revoked"
