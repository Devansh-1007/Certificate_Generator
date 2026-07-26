"""
Multi-tenant data access: organisations, users and memberships.

Design notes
------------
* An **organisation** is the tenant and owns all data. A **user** is a person
  who signs in with email + password and belongs to exactly one organisation
  with a role (owner / admin / member).
* `org_id` is never accepted from the client. It is read from the verified JWT
  and applied server-side, so a caller cannot address another tenant's data
  by guessing ids.
* Helpers here are request-free (no Flask globals) so routes, the bulk worker
  thread and tests can all call them.
"""

import re
import uuid
import logging
import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from dataHandling import configureMySQL

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

ROLES = ("owner", "admin", "member")
ROLE_RANK = {"member": 0, "admin": 1, "owner": 2}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class TenancyError(Exception):
    """Domain error with a message that is safe to show the user."""


def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:60] or "org"


def validate_signup(email, password, org_name):
    if not EMAIL_RE.match((email or "").strip()):
        raise TenancyError("Enter a valid email address.")
    if len(password or "") < 8:
        raise TenancyError("Password must be at least 8 characters.")
    if len((org_name or "").strip()) < 2:
        raise TenancyError("Organisation name is required.")


def _unique_slug(cur, base):
    """Slugs are user-visible; append a counter rather than failing signup."""
    slug, n = base, 1
    while True:
        cur.execute("SELECT 1 FROM ORGANISATIONS WHERE SLUG=%s", (slug,))
        if not cur.fetchone():
            return slug
        n += 1
        slug = "{}-{}".format(base[:55], n)


def create_organisation(org_name, email, password, full_name=None):
    """
    Self-serve signup: creates the organisation and its first user (owner)
    in one transaction. Returns the new user record.
    """
    validate_signup(email, password, org_name)
    email = email.strip().lower()

    db = configureMySQL()
    cur = db.cursor()
    try:
        cur.execute("SELECT 1 FROM USERS WHERE EMAIL=%s", (email,))
        if cur.fetchone():
            raise TenancyError("An account with that email already exists.")

        org_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        slug = _unique_slug(cur, slugify(org_name))

        cur.execute(
            "INSERT INTO ORGANISATIONS (ORG_ID, NAME, SLUG, PLAN) VALUES (%s,%s,%s,'free')",
            (org_id, org_name.strip(), slug),
        )
        cur.execute(
            "INSERT INTO USERS (USER_ID, ORG_ID, EMAIL, FULL_NAME, PASSWORD_HASH, ROLE) "
            "VALUES (%s,%s,%s,%s,%s,'owner')",
            (user_id, org_id, email, (full_name or "").strip() or None,
             generate_password_hash(password)),
        )
        db.commit()
        logging.info("Organisation '%s' created (%s) with owner %s", org_name, slug, email)
        return {
            "USER_ID": user_id, "ORG_ID": org_id, "EMAIL": email,
            "FULL_NAME": full_name, "ROLE": "owner", "ORG_NAME": org_name.strip(),
            "ORG_SLUG": slug, "PLAN": "free",
        }
    except TenancyError:
        db.rollback()
        raise
    except Exception as e:  # noqa: BLE001
        db.rollback()
        logging.error("Signup failed for %s: %s", email, e)
        raise TenancyError("Could not create the account. Please try again.")
    finally:
        cur.close()
        db.close()


def authenticate(email, password):
    """Verify credentials and return the user + their organisation, or None."""
    email = (email or "").strip().lower()
    db = configureMySQL()
    cur = db.cursor()
    try:
        cur.execute(
            "SELECT u.USER_ID, u.ORG_ID, u.EMAIL, u.FULL_NAME, u.PASSWORD_HASH, u.ROLE, "
            "       u.STATUS, o.NAME, o.SLUG, o.PLAN, o.STATUS "
            "FROM USERS u JOIN ORGANISATIONS o ON o.ORG_ID = u.ORG_ID WHERE u.EMAIL=%s",
            (email,),
        )
        row = cur.fetchone()
        if not row or not check_password_hash(row[4], password or ""):
            return None
        if row[6] != "active" or row[10] != "active":
            raise TenancyError("This account is suspended. Contact your organisation owner.")

        cur.execute("UPDATE USERS SET LAST_LOGIN_ON=%s WHERE USER_ID=%s",
                    (datetime.datetime.utcnow(), row[0]))
        db.commit()
        return {
            "USER_ID": row[0], "ORG_ID": row[1], "EMAIL": row[2], "FULL_NAME": row[3],
            "ROLE": row[5], "ORG_NAME": row[7], "ORG_SLUG": row[8], "PLAN": row[9],
        }
    finally:
        cur.close()
        db.close()


def get_organisation(org_id):
    db = configureMySQL()
    cur = db.cursor()
    try:
        cur.execute(
            "SELECT ORG_ID, NAME, SLUG, PLAN, BRAND_COLOR, LOGO_URL, STATUS, CREATED_ON "
            "FROM ORGANISATIONS WHERE ORG_ID=%s",
            (org_id,),
        )
        r = cur.fetchone()
        if not r:
            return None
        return {
            "ORG_ID": r[0], "NAME": r[1], "SLUG": r[2], "PLAN": r[3],
            "BRAND_COLOR": r[4], "LOGO_URL": r[5], "STATUS": r[6], "CREATED_ON": str(r[7]),
        }
    finally:
        cur.close()
        db.close()


def update_organisation(org_id, name=None, brand_color=None, logo_url=None):
    fields, values = [], []
    if name is not None:
        if len(name.strip()) < 2:
            raise TenancyError("Organisation name is too short.")
        fields.append("NAME=%s")
        values.append(name.strip())
    if brand_color is not None:
        if brand_color and not re.match(r"^#[0-9A-Fa-f]{6}$", brand_color):
            raise TenancyError("Brand colour must be a hex value like #B08D57.")
        fields.append("BRAND_COLOR=%s")
        values.append(brand_color or None)
    if logo_url is not None:
        fields.append("LOGO_URL=%s")
        values.append(logo_url or None)
    if not fields:
        return get_organisation(org_id)

    db = configureMySQL()
    cur = db.cursor()
    try:
        cur.execute(
            "UPDATE ORGANISATIONS SET {}, UPDATED_ON=NOW() WHERE ORG_ID=%s".format(", ".join(fields)),
            (*values, org_id),
        )
        db.commit()
    finally:
        cur.close()
        db.close()
    return get_organisation(org_id)


def list_members(org_id):
    db = configureMySQL()
    cur = db.cursor()
    try:
        cur.execute(
            "SELECT USER_ID, EMAIL, FULL_NAME, ROLE, STATUS, LAST_LOGIN_ON, CREATED_ON "
            "FROM USERS WHERE ORG_ID=%s ORDER BY CREATED_ON",
            (org_id,),
        )
        return [
            {
                "USER_ID": r[0], "EMAIL": r[1], "FULL_NAME": r[2], "ROLE": r[3],
                "STATUS": r[4], "LAST_LOGIN_ON": str(r[5]) if r[5] else None,
                "CREATED_ON": str(r[6]),
            }
            for r in cur.fetchall()
        ]
    finally:
        cur.close()
        db.close()


def invite_member(org_id, email, password, role="member", full_name=None):
    """Owner/admin adds a teammate directly (no email delivery in this build)."""
    if role not in ROLES:
        raise TenancyError("Role must be one of: {}.".format(", ".join(ROLES)))
    validate_signup(email, password, "placeholder-org")
    email = email.strip().lower()

    db = configureMySQL()
    cur = db.cursor()
    try:
        cur.execute("SELECT 1 FROM USERS WHERE EMAIL=%s", (email,))
        if cur.fetchone():
            raise TenancyError("That email is already registered.")
        user_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO USERS (USER_ID, ORG_ID, EMAIL, FULL_NAME, PASSWORD_HASH, ROLE) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (user_id, org_id, email, (full_name or "").strip() or None,
             generate_password_hash(password), role),
        )
        db.commit()
        return {"USER_ID": user_id, "EMAIL": email, "ROLE": role}
    finally:
        cur.close()
        db.close()


def update_member(org_id, user_id, role=None, status=None):
    """
    Change a teammate's role or status. Refuses to remove the last owner —
    an organisation with no owner can never be administered again.
    """
    if role is not None and role not in ROLES:
        raise TenancyError("Role must be one of: {}.".format(", ".join(ROLES)))

    db = configureMySQL()
    cur = db.cursor()
    try:
        cur.execute("SELECT ROLE FROM USERS WHERE USER_ID=%s AND ORG_ID=%s", (user_id, org_id))
        row = cur.fetchone()
        if not row:
            raise TenancyError("No such member in this organisation.")

        demoting_owner = row[0] == "owner" and ((role and role != "owner") or status == "suspended")
        if demoting_owner:
            cur.execute(
                "SELECT COUNT(*) FROM USERS WHERE ORG_ID=%s AND ROLE='owner' AND STATUS='active'",
                (org_id,),
            )
            if cur.fetchone()[0] <= 1:
                raise TenancyError("An organisation must keep at least one active owner.")

        sets, values = [], []
        if role is not None:
            sets.append("ROLE=%s")
            values.append(role)
        if status is not None:
            sets.append("STATUS=%s")
            values.append(status)
        if sets:
            cur.execute(
                "UPDATE USERS SET {} WHERE USER_ID=%s AND ORG_ID=%s".format(", ".join(sets)),
                (*values, user_id, org_id),
            )
            db.commit()
        return True
    finally:
        cur.close()
        db.close()


def org_usage(org_id):
    """Counts for the organisation dashboard (and, later, plan quotas)."""
    db = configureMySQL()
    cur = db.cursor()
    try:
        out = {}
        for key, table in (
            ("CERTIFICATES", "CERTIFICATE_DETAILS"),
            ("ID_CARDS", "ID_DETAILS"),
            ("TEMPLATES", "TEMPLATE_DETAILS"),
            ("BATCHES", "BATCH_JOBS"),
        ):
            try:
                cur.execute("SELECT COUNT(*) FROM `{}` WHERE ORG_ID=%s".format(table), (org_id,))
                out[key] = cur.fetchone()[0]
            except Exception:  # noqa: BLE001 - table may not exist yet
                out[key] = 0
        cur.execute("SELECT COUNT(*) FROM USERS WHERE ORG_ID=%s AND STATUS='active'", (org_id,))
        out["MEMBERS"] = cur.fetchone()[0]
        return out
    finally:
        cur.close()
        db.close()
