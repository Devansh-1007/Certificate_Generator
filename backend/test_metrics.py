"""Offline tests for the telemetry collector behind the admin console."""

import time

import metrics


def _reset():
    metrics._samples.clear()
    metrics._errors.clear()
    metrics._incidents.clear()
    metrics._last_component_status.clear()


def test_snapshot_aggregates_counts_and_error_rate():
    _reset()
    for _ in range(8):
        metrics.record_request("/generateCertificate", "POST", 200, 120.0)
    for _ in range(2):
        metrics.record_request("/generateCertificate", "POST", 500, 900.0)

    snap = metrics.snapshot(window_seconds=60, buckets=6)
    assert snap["TOTAL_REQUESTS"] == 10
    assert snap["ERROR_COUNT"] == 2 and snap["SERVER_ERROR_COUNT"] == 2
    assert snap["ERROR_RATE"] == 20.0
    assert snap["P50_MS"] <= snap["P95_MS"] <= snap["P99_MS"]


def test_snapshot_series_has_requested_buckets():
    _reset()
    metrics.record_request("/x", "GET", 200, 10.0)
    snap = metrics.snapshot(window_seconds=300, buckets=12)
    assert len(snap["SERIES"]) == 12
    assert sum(b["REQUESTS"] for b in snap["SERIES"]) == 1


def test_endpoint_table_ranks_by_volume():
    _reset()
    for _ in range(5):
        metrics.record_request("/busy", "GET", 200, 50.0)
    metrics.record_request("/quiet", "GET", 200, 50.0)
    snap = metrics.snapshot(window_seconds=60)
    assert snap["ENDPOINTS"][0]["PATH"] == "/busy"
    assert snap["ENDPOINTS"][0]["COUNT"] == 5


def test_old_samples_fall_out_of_the_window():
    _reset()
    metrics._samples.append((time.time() - 5000, "/old", "GET", 200, 10.0))
    metrics.record_request("/new", "GET", 200, 10.0)
    snap = metrics.snapshot(window_seconds=60)
    assert snap["TOTAL_REQUESTS"] == 1


def test_incidents_log_only_transitions():
    _reset()
    assert metrics.record_health("database", "up") is False      # first observation
    assert metrics.record_health("database", "up") is False       # unchanged
    assert metrics.record_health("database", "down", "refused") is True   # transition
    assert metrics.record_health("database", "up") is True                # recovery
    snap = metrics.snapshot()
    assert len(snap["INCIDENTS"]) == 2
    assert snap["INCIDENTS"][0]["STATUS"] == "up"  # newest first


def test_buffers_are_bounded():
    _reset()
    for i in range(metrics.MAX_SAMPLES + 50):
        metrics.record_request("/x", "GET", 200, 1.0)
    assert len(metrics._samples) == metrics.MAX_SAMPLES
