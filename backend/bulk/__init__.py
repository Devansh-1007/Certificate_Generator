"""
Bulk certificate pipeline: parse a CSV/Excel roster, run the anomaly agent
(maker-checker review), then batch-render each row through the template engine.
"""

from bulk.parser import (
    parse_table,
    map_rows,
    detect_anomalies,
    suggest_rows,
    ParseError,
)

__all__ = [
    "parse_table",
    "map_rows",
    "detect_anomalies",
    "suggest_rows",
    "ParseError",
]
