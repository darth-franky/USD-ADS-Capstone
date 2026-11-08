#!/usr/bin/env python3
"""Download the CISO hourly demand series from the official EIA API.

The UTC range maps exactly to Pacific local calendar years 2019 through 2025.
The script writes newline-delimited JSON so the raw response remains auditable.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
DEFAULT_OUTPUT = Path("data/raw/eia930_ciso_demand_2019_2025.jsonl")
START_UTC = "2019-01-01T08"
END_UTC = "2026-01-01T07"
PAGE_SIZE = 5000


def build_url(api_key: str, offset: int) -> str:
    params = [
        ("api_key", api_key),
        ("frequency", "hourly"),
        ("data[0]", "value"),
        ("facets[respondent][]", "CISO"),
        ("facets[type][]", "D"),
        ("start", START_UTC),
        ("end", END_UTC),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "asc"),
        ("offset", str(offset)),
        ("length", str(PAGE_SIZE)),
    ]
    return f"{API_URL}?{urllib.parse.urlencode(params)}"


def fetch_page(api_key: str, offset: int) -> dict:
    for attempt in range(7):
        request = urllib.request.Request(
            build_url(api_key, offset),
            headers={"User-Agent": "USD-ADS-599-Capstone/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 6:
                raise
            retry_after = error.headers.get("Retry-After")
            wait_seconds = float(retry_after) if retry_after else 2 ** (attempt + 1)
            print(f"rate limited; retrying offset {offset:,} in {wait_seconds:.0f} seconds")
            time.sleep(wait_seconds)
    raise RuntimeError("unreachable retry state")


def download(output: Path, api_key: str) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    total: int | None = None
    offset = 0

    while total is None or offset < total:
        payload = fetch_page(api_key, offset)
        response = payload.get("response", {})
        page = response.get("data", [])
        total = int(response.get("total", 0))
        if not page and offset < total:
            raise RuntimeError(f"EIA returned an empty page at offset {offset} of {total}")
        rows.extend(page)
        offset += len(page)
        print(f"downloaded {len(rows):,} of {total:,} rows")
        if page and offset < total:
            time.sleep(1.0)

    if len(rows) != total:
        raise RuntimeError(f"Expected {total} rows but received {len(rows)}")

    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    api_key = os.environ.get("EIA_API_KEY", "DEMO_KEY")
    count = download(args.output, api_key)
    print(f"wrote {count:,} rows to {args.output}")


if __name__ == "__main__":
    main()

