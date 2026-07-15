"""
Verifiable certificates.

Every generated certificate gets a short, unguessable UID and an HMAC-SHA256
signature over its identifying fields (uid, client, recipient, event, date).
The certificate's QR encodes {BASE_URL}/verify/<uid>; a PUBLIC endpoint looks
the UID up, recomputes the signature, and reports genuine / tampered / revoked.

Signing is keyed by VERIFY_SECRET (falls back to JWT_SECRET, then a dev key),
so the stored record is tamper-evident even to someone with DB read access.

DB helpers here are request-free (no Flask `request`) so both the single-cert
route and the bulk worker thread can call them.
"""

import os
import hmac
import base64
import hashlib
import logging
import secrets

from dataHandling import configureMySQL

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def _secret():
    return (os.getenv("VERIFY_SECRET")
            or os.getenv("JWT_SECRET")
            or "dev-secret-change-me").encode("utf-8")


def new_uid():
    """Short, URL-safe, unguessable id (~13 chars)."""
    return secrets.token_urlsafe(9)


def sign(uid, client_id, recipient, event, issue_date):
    """Deterministic HMAC-SHA256 over the canonical field payload."""
    payload = "|".join([
        uid or "", client_id or "", recipient or "", event or "", issue_date or "",
    ]).encode("utf-8")
    digest = hmac.new(_secret(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def verify_signature(record):
    """Constant-time check that a stored record's signature still matches its fields."""
    expected = sign(
        record.get("CERT_UID"), record.get("CLIENT_ID"), record.get("RECIPIENT_NAME"),
        record.get("EVENT_NAME"), record.get("ISSUE_DATE"),
    )
    return hmac.compare_digest(expected, record.get("SIGNATURE") or "")


# --------------------------------------------------------------------------- #
# Persistence (request-free)
# --------------------------------------------------------------------------- #

def create_record(client_id, recipient, event, issue_date):
    """
    Insert a verification record and return (uid, signature). Best-effort: if the
    DB is unavailable the caller still gets a signed uid so rendering can proceed.
    """
    uid = new_uid()
    signature = sign(uid, client_id, recipient, event, issue_date)
    try:
        db = configureMySQL()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO CERTIFICATE_VERIFY "
            "(`CERT_UID`,`CLIENT_ID`,`RECIPIENT_NAME`,`EVENT_NAME`,`ISSUE_DATE`,"
            "`SIGNATURE`,`STATUS`) VALUES (%s,%s,%s,%s,%s,%s,'VALID')",
            (uid, client_id, recipient, event, issue_date, signature),
        )
        db.commit()
    except Exception as e:  # noqa: BLE001 - storage optional in local dev
        logging.warning("Verification record not persisted (%s)", e)
    return uid, signature


def get_record(uid):
    db = configureMySQL()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM CERTIFICATE_VERIFY WHERE CERT_UID=%s", (uid,))
    return cur.fetchone()


def list_records(client_id):
    db = configureMySQL()
    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT CERT_UID, RECIPIENT_NAME, EVENT_NAME, ISSUE_DATE, STATUS, CREATED_ON "
        "FROM CERTIFICATE_VERIFY WHERE CLIENT_ID=%s ORDER BY CREATED_ON DESC",
        (client_id,),
    )
    return cur.fetchall()


def set_status(client_id, uid, status):
    """Revoke / reinstate. Returns True if a row owned by this client was updated."""
    db = configureMySQL()
    cur = db.cursor()
    cur.execute(
        "UPDATE CERTIFICATE_VERIFY SET STATUS=%s WHERE CERT_UID=%s AND CLIENT_ID=%s",
        (status, uid, client_id),
    )
    db.commit()
    return cur.rowcount > 0


def public_result(uid):
    """
    Build the public verification payload for a UID:
      - not found        -> {"valid": False, "reason": "not_found"}
      - signature broken -> {"valid": False, "reason": "tampered"}
      - revoked          -> {"valid": False, "reason": "revoked", ...details}
      - genuine          -> {"valid": True, ...details}
    """
    record = get_record(uid)
    if not record:
        return {"valid": False, "reason": "not_found"}

    details = {
        "uid": record["CERT_UID"],
        "recipient": record["RECIPIENT_NAME"],
        "event": record["EVENT_NAME"],
        "issue_date": record["ISSUE_DATE"],
        "issuer": record["CLIENT_ID"],
        "issued_on": str(record.get("CREATED_ON")),
    }
    if not verify_signature(record):
        return {"valid": False, "reason": "tampered", **details}
    if (record.get("STATUS") or "VALID").upper() != "VALID":
        return {"valid": False, "reason": "revoked", **details}
    return {"valid": True, **details}
