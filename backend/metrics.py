"""
In-process telemetry: request metrics, uptime tracking and an incident log.

Deliberately dependency-free and bounded. Everything lives in fixed-size
deques behind a lock, so memory is capped and the collector is safe to call
from Flask's request hooks and the bulk worker thread alike.

This is per-process telemetry (a single Render instance), not a replacement
for Prometheus/Grafana — the point is that the admin can see health, load and
failures without leaving the app.
"""

import time
import threading
from collections import deque, defaultdict

# ~1000 requests of history is plenty for a dashboard and stays small in RAM.
MAX_SAMPLES = 1000
MAX_ERRORS = 100
MAX_INCIDENTS = 50

_lock = threading.Lock()
_started_at = time.time()

# (timestamp, path, method, status, duration_ms)
_samples = deque(maxlen=MAX_SAMPLES)
# (timestamp, path, method, status, message)
_errors = deque(maxlen=MAX_ERRORS)
# (timestamp, component, status, detail) — health transitions only
_incidents = deque(maxlen=MAX_INCIDENTS)

# component -> last known status, so we only log transitions rather than every probe
_last_component_status = {}


def record_request(path, method, status, duration_ms):
    with _lock:
        _samples.append((time.time(), path, method, int(status), float(duration_ms)))


def record_error(path, method, status, message):
    with _lock:
        _errors.append((time.time(), path, method, int(status), str(message)[:300]))


def record_health(component, status, detail=""):
    """Log only when a component changes state — that's what an incident is."""
    with _lock:
        previous = _last_component_status.get(component)
        _last_component_status[component] = status
        if previous is not None and previous != status:
            _incidents.append((time.time(), component, status, detail[:200]))
            return True
        return False


def _percentile(values, pct):
    if not values:
        return 0.0
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return round(ordered[k], 1)


def snapshot(window_seconds=900, buckets=30):
    """
    Summarise the recent window for the admin dashboard.

    Returns totals, error rate, latency percentiles, a per-endpoint table and a
    bucketed time series (traffic + errors + latency) the UI charts directly.
    """
    now = time.time()
    cutoff = now - window_seconds
    with _lock:
        samples = [s for s in _samples if s[0] >= cutoff]
        errors = list(_errors)
        incidents = list(_incidents)
        started = _started_at

    durations = [s[4] for s in samples]
    failed = [s for s in samples if s[3] >= 400]
    server_errors = [s for s in samples if s[3] >= 500]

    # per-endpoint aggregation
    by_ep = defaultdict(lambda: {"count": 0, "errors": 0, "total_ms": 0.0, "max_ms": 0.0})
    for _ts, path, _m, status, ms in samples:
        e = by_ep[path]
        e["count"] += 1
        e["total_ms"] += ms
        e["max_ms"] = max(e["max_ms"], ms)
        if status >= 400:
            e["errors"] += 1
    endpoints = sorted(
        (
            {
                "PATH": p,
                "COUNT": v["count"],
                "ERRORS": v["errors"],
                "AVG_MS": round(v["total_ms"] / v["count"], 1),
                "MAX_MS": round(v["max_ms"], 1),
            }
            for p, v in by_ep.items()
        ),
        key=lambda r: -r["COUNT"],
    )[:12]

    # time series
    span = max(1.0, window_seconds / float(buckets))
    series = []
    for i in range(buckets):
        b_start = cutoff + i * span
        b_end = b_start + span
        in_bucket = [s for s in samples if b_start <= s[0] < b_end]
        b_durations = [s[4] for s in in_bucket]
        series.append({
            "T": int(b_end),
            "REQUESTS": len(in_bucket),
            "ERRORS": len([s for s in in_bucket if s[3] >= 400]),
            "P95_MS": _percentile(b_durations, 95),
        })

    uptime_s = now - started
    return {
        "UPTIME_SECONDS": int(uptime_s),
        "STARTED_AT": int(started),
        "WINDOW_SECONDS": window_seconds,
        "TOTAL_REQUESTS": len(samples),
        "ERROR_COUNT": len(failed),
        "SERVER_ERROR_COUNT": len(server_errors),
        "ERROR_RATE": round(100.0 * len(failed) / len(samples), 2) if samples else 0.0,
        "AVG_MS": round(sum(durations) / len(durations), 1) if durations else 0.0,
        "P50_MS": _percentile(durations, 50),
        "P95_MS": _percentile(durations, 95),
        "P99_MS": _percentile(durations, 99),
        "SERIES": series,
        "ENDPOINTS": endpoints,
        "RECENT_ERRORS": [
            {"T": int(t), "PATH": p, "METHOD": m, "STATUS": s, "MESSAGE": msg}
            for t, p, m, s, msg in list(reversed(errors))[:20]
        ],
        "INCIDENTS": [
            {"T": int(t), "COMPONENT": c, "STATUS": s, "DETAIL": d}
            for t, c, s, d in list(reversed(incidents))[:20]
        ],
    }


def install(app):
    """Wire request timing into Flask. Skips CORS preflight and the probes themselves."""
    from flask import request, g as flask_g

    @app.before_request
    def _start_timer():
        flask_g._metrics_start = time.perf_counter()

    @app.after_request
    def _record(response):
        start = getattr(flask_g, "_metrics_start", None)
        if start is not None and request.method != "OPTIONS":
            ms = (time.perf_counter() - start) * 1000.0
            path = request.url_rule.rule if request.url_rule else request.path
            record_request(path, request.method, response.status_code, ms)
            if response.status_code >= 400:
                record_error(path, request.method, response.status_code,
                             response.status.replace(str(response.status_code), "").strip())
        return response

    return app
