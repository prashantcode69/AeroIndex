import json
import sys
from pathlib import Path
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_args():
    """
    Example:
    python deduplicate_google_fares.py DEL BOM
    """

    if len(sys.argv) >= 3:
        origin = sys.argv[1].upper()
        destination = sys.argv[2].upper()
    else:
        origin = "DEL"
        destination = "BOM"

    return origin, destination


def get_output_file(origin, destination):
    return Path("data/raw") / f"{origin}_{destination}_fares_cleaned.json"


def load_all_window_records(origin, destination):
    """
    Har booking window apni alag raw file mein extract hui thi
    (parallel scraping ke liye) - sabko yahan merge karte hain.

    Example matches: data/raw/DEL_BOM_fares_raw_7.json, ..._15.json, etc.
    """

    raw_dir = Path("data/raw")
    pattern = f"{origin}_{destination}_fares_raw_*.json"

    records = []

    for window_file in sorted(raw_dir.glob(pattern)):
        with window_file.open("r", encoding="utf-8") as f:
            records.extend(json.load(f))

    return records


def main():
    origin, destination = get_args()
    output_file = get_output_file(origin, destination)

    records = load_all_window_records(origin, destination)

    grouped = defaultdict(list)

    for record in records:
        key = (
            record["source"],
            record["airline"],
            record["origin"],
            record["destination"],
            record["departure_date"],
            record["booking_window"],
        )

        grouped[key].append(record)

    cleaned_records = []

    for key, items in grouped.items():
        # Same airline/route/window ke duplicate fares hatao
        unique_fares = sorted(
            set(item["fare"] for item in items)
        )

        base_record = items[0]

        for fare in unique_fares:
            new_record = base_record.copy()
            new_record["fare"] = fare
            new_record["observations"] = sum(
                1 for item in items if item["fare"] == fare
            )
            cleaned_records.append(new_record)

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(cleaned_records, f, indent=2, ensure_ascii=False)

    print(f"Original records: {len(records)}")
    print(f"Cleaned records: {len(cleaned_records)}")
    print(f"Saved to: {output_file}")

    print("\nCleaned fares:")
    for record in cleaned_records:
        print(
            f'{record["airline"]}: ₹{record["fare"]:,} '
            f'(window: {record["booking_window"]}d, '
            f'{record["observations"]} observations)'
        )


if __name__ == "__main__":
    main()
