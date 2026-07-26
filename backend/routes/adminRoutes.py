"""
Admin operations console — all routes require an admin JWT.

GET  /admin/health     live probes: MySQL, object storage, LLM config (+ latency)
GET  /admin/metrics    request volume, error rate, latency percentiles, incidents
GET  /admin/database   server version/uptime, per-table row counts and sizes
GET  /admin/clients    registered clients with their certificate/ID/template counts
POST /admin/probe      force a health probe now (used by the dashboard's refresh)
"""

import os
import time
import logging
import platform

from flask import Blueprint, jsonify, request

import metrics
from middleware import require_admin
from config import bucket, mysql_db, mysql_host

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

admin_bp = Blueprint("admin", __name__)

# Tables the dashboard reports on, in a sensible reading order.
TRACKED_TABLES = [
    "CLIENT_DETAILS",
    "CERTIFICATE_DETAILS",
    "ID_DETAILS",
    "TEMPLATE_DETAILS",
    "CERTIFICATE_VERIFY",
    "BATCH_JOBS",
]


def _timed(fn):
    """Run a probe, returning (ok, latency_ms, detail) without ever raising."""
    start = time.perf_counter()
    try:
        detail = fn() or ""
        return True, round((time.perf_counter() - start) * 1000, 1), detail
    except Exception as e:  # noqa: BLE001 - a probe failure is a result, not a crash
        return False, round((time.perf_counter() - start) * 1000, 1), str(e)[:200]


def _probe_mysql():
    from dataHandling import configureMySQL

    db = configureMySQL()
    cur = db.cursor()
    cur.execute("SELECT VERSION()")
    version = cur.fetchone()[0]
    cur.close()
    db.close()
    return "MySQL " + str(version)


def _probe_storage():
    if not bucket:
        raise RuntimeError("BUCKET not configured")
    from awsS3 import _client

    _client().head_bucket(Bucket=bucket)
    return "bucket '{}' reachable".format(bucket)


def _probe_llm():
    """Config check only — a real completion would burn rate-limited tokens."""
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    key_var = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}.get(provider)
    if provider != "ollama" and not os.getenv(key_var or ""):
        raise RuntimeError("{} is not set".format(key_var))
    return "{} · {}".format(provider, os.getenv("LLM_MODEL", "default model"))


@admin_bp.route("/admin/health", methods=["GET"])
@require_admin
def health():
    checks = []
    for name, fn in (
        ("database", _probe_mysql),
        ("storage", _probe_storage),
        ("llm", _probe_llm),
    ):
        ok, ms, detail = _timed(fn)
        status = "up" if ok else "down"
        metrics.record_health(name, status, detail)
        checks.append({"COMPONENT": name, "STATUS": status, "LATENCY_MS": ms, "DETAIL": detail})

    overall = "up" if all(c["STATUS"] == "up" for c in checks) else (
        "degraded" if any(c["STATUS"] == "up" for c in checks) else "down"
    )
    return jsonify({
        "STATUS": overall,
        "CHECKS": checks,
        "RUNTIME": {
            "PYTHON": platform.python_version(),
            "HOST": platform.node(),
            "DB_HOST": mysql_host,
            "DB_NAME": mysql_db,
            "BASE_URL": os.getenv("BASE_URL", ""),
        },
        "CHECKED_AT": int(time.time()),
    })


@admin_bp.route("/admin/metrics", methods=["GET"])
@require_admin
def metrics_view():
    try:
        window = max(60, min(86400, int(request.args.get("WINDOW", 900))))
    except ValueError:
        window = 900
    return jsonify(metrics.snapshot(window_seconds=window))


@admin_bp.route("/admin/database", methods=["GET"])
@require_admin
def database():
    from dataHandling import configureMySQL

    try:
        db = configureMySQL()
        cur = db.cursor()

        cur.execute("SELECT VERSION()")
        version = cur.fetchone()[0]
        cur.execute("SHOW GLOBAL STATUS LIKE 'Uptime'")
        row = cur.fetchone()
        db_uptime = int(row[1]) if row else 0
        cur.execute("SHOW GLOBAL STATUS LIKE 'Threads_connected'")
        row = cur.fetchone()
        connections = int(row[1]) if row else 0

        # Sizes come from information_schema; row counts are exact per table.
        cur.execute(
            "SELECT TABLE_NAME, ROUND((DATA_LENGTH + INDEX_LENGTH)/1024, 1) "
            "FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s",
            (mysql_db,),
        )
        sizes = {name: float(kb or 0) for name, kb in cur.fetchall()}

        tables = []
        for table in TRACKED_TABLES:
            try:
                cur.execute("SELECT COUNT(*) FROM `{}`".format(table))
                count = cur.fetchone()[0]
                present = True
            except Exception:  # noqa: BLE001 - a missing table is information, not an error
                count, present = 0, False
            tables.append({
                "TABLE": table, "ROWS": count,
                "SIZE_KB": sizes.get(table, 0.0), "PRESENT": present,
            })

        cur.close()
        db.close()
        return jsonify({
            "STATUS": "up",
            "VERSION": str(version),
            "UPTIME_SECONDS": db_uptime,
            "CONNECTIONS": connections,
            "SCHEMA": mysql_db,
            "TABLES": tables,
            "MIGRATIONS_APPLIED": all(t["PRESENT"] for t in tables),
        })
    except Exception as e:  # noqa: BLE001
        logging.error("Admin database view failed: %s", e)
        return jsonify({"STATUS": "down", "description": str(e)[:300]}), 503


@admin_bp.route("/admin/clients", methods=["GET"])
@require_admin
def clients():
    from dataHandling import configureMySQL

    try:
        db = configureMySQL()
        cur = db.cursor()
        cur.execute(
            "SELECT c.CLIENT_ID, c.CLIENT_NAME, c.CREATED_ON, "
            "  (SELECT COUNT(*) FROM CERTIFICATE_DETAILS x WHERE x.CLIENT_ID = c.CLIENT_ID), "
            "  (SELECT COUNT(*) FROM ID_DETAILS x WHERE x.CLIENT_ID = c.CLIENT_ID), "
            "  (SELECT COUNT(*) FROM TEMPLATE_DETAILS x WHERE x.CLIENT_ID = c.CLIENT_ID) "
            "FROM CLIENT_DETAILS c ORDER BY c.CREATED_ON DESC"
        )
        rows = cur.fetchall()
        cur.close()
        db.close()
        return jsonify({
            "CLIENTS": [
                {
                    "CLIENT_ID": r[0], "CLIENT_NAME": r[1], "CREATED_ON": str(r[2]),
                    "CERTIFICATES": r[3], "ID_CARDS": r[4], "TEMPLATES": r[5],
                }
                for r in rows
            ]
        })
    except Exception as e:  # noqa: BLE001
        logging.error("Admin clients view failed: %s", e)
        return jsonify({"description": str(e)[:300]}), 503


@admin_bp.route("/admin/probe", methods=["POST"])
@require_admin
def probe():
    return health()
