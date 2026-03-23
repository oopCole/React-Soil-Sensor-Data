"""Convert exported Soil Testing Google Sheet CSV to src/data/soil-data.json."""
from __future__ import annotations

import csv
import json
from pathlib import Path


def row_to_point(cols: list[str], start: int) -> dict:
    return {
        "t": int(float(cols[start])),
        "moisture": float(cols[start + 1]),
        "tempC": float(cols[start + 2]),
        "ecMicroSiemens": float(cols[start + 3]),
        "ph": float(cols[start + 4]),
        "nitrogenMgKg": float(cols[start + 5]),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_path = Path(__file__).with_name("sheet.csv")
    out_path = root / "src" / "data" / "soil-data.json"
    huntsville: list[dict] = []
    uncc: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    for i, cols in enumerate(rows):
        if i < 2:
            continue
        if len(cols) < 13:
            continue
        try:
            huntsville.append(row_to_point(cols, 0))
            uncc.append(row_to_point(cols, 7))
        except (ValueError, IndexError):
            continue
    payload = {
        "source": "https://docs.google.com/spreadsheets/d/17GL9VDrRStllIhly6Wa1WXqT6rtxqu071V3waARuHmY/edit?usp=sharing",
        "notes": {
            "moistureScale": "0–0.5 (sheet: (raw - 200)/1800)",
            "locations": [
                "Huntsville",
                "UNCC",
            ],
        },
        "series": {
            "huntsville": huntsville,
            "uncc": uncc,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(huntsville)} rows -> {out_path}")


if __name__ == "__main__":
    main()
