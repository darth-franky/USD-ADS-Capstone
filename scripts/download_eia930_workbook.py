#!/usr/bin/env python3
"""Download EIA's official full-history CISO workbook without an API key."""

from __future__ import annotations

import argparse
import shutil
import urllib.request
from pathlib import Path


URL = "https://www.eia.gov/electricity/gridmonitor/knownissues/xls/CISO.xlsx"
DEFAULT_OUTPUT = Path("data/raw/EIA930_CISO.xlsx")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".xlsx.part")
    request = urllib.request.Request(URL, headers={"User-Agent": "USD-ADS-599-Capstone/1.0"})
    with urllib.request.urlopen(request, timeout=180) as response, temporary.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    temporary.replace(args.output)
    print(f"wrote {args.output} ({args.output.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
