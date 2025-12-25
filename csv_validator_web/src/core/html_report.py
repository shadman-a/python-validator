from __future__ import annotations

from pathlib import Path


def write_html_report(path: Path, report: dict) -> None:
    html = [
        "<html><head><title>CSV Validation Report</title></head><body>",
        "<h1>CSV Validation Report</h1>",
        f"<pre>{report}</pre>",
        "</body></html>",
    ]
    path.write_text("\n".join(html))
