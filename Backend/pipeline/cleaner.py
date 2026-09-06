import json
import sys
from pathlib import Path
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


BASE_DIR = Path(__file__).resolve().parent.parent

# Existing app compatibility ke liye
OUTPUT_FILE = BASE_DIR / "data/cleaned/flights_cleaned.json"


def get_args():
    """
    Example:
    python cleaner.py DEL GOI
    """

    if len(sys.argv) >= 3:
        origin = sys.argv[1].upper()
        destination = sys.argv[2].upper()
    else:
        origin = "DEL"
        destination = "BOM"

    return origin, destination


def get_raw_file(origin, destination):
    return (
        BASE_DIR
        / "data"
        / "raw"
        / f"{origin}_{destination}_fares_cleaned.json"
    )


def get_route_output_file(origin, destination):
    """
    Example:
    data/routes/DEL_GOI/flights_cleaned.json
    """

    route_folder = (
        BASE_DIR
        / "data"
        / "routes"
        / f"{origin}_{destination}"
    )

    route_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    return route_folder / "flights_cleaned.json"


def load_fares(raw_file):
    if not raw_file.exists():
        raise FileNotFoundError(
            f"File not found: {raw_file}"
        )

    with raw_file.open(
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def clean_fares(records):
    cleaned = []

    for record in records:
        fare = record.get("fare")

        if not isinstance(fare, (int, float)):
            continue

        if fare <= 0:
            continue

        cleaned_record = {
            "source": record.get(
                "source",
                "Unknown"
            ),
            "airline": record.get(
                "airline",
                "Unknown"
            ),
            "origin": record.get(
                "origin"
            ),
            "destination": record.get(
                "destination"
            ),
            "departure_date": record.get(
                "departure_date"
            ),
            "booking_window": record.get(
                "booking_window"
            ),
            "fare": round(
                float(fare),
                2
            ),
            "currency": record.get(
                "currency",
                "INR"
            ),
            "collected_at": record.get(
                "collected_at",
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }

        cleaned.append(cleaned_record)

    return cleaned


def save_fares(
    records,
    origin,
    destination
):
    # Route-wise output
    route_output_file = get_route_output_file(
        origin,
        destination
    )

    with route_output_file.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            records,
            f,
            indent=2,
            ensure_ascii=False
        )

    # Existing app ke liye same old output bhi save hoga
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            records,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Cleaned records: {len(records)}")
    print(
        f"Route-wise file saved to: "
        f"{route_output_file}"
    )
    print(
        f"Compatibility file saved to: "
        f"{OUTPUT_FILE}"
    )


def main():
    origin, destination = get_args()

    print("\n" + "=" * 60)
    print("ROUTE-WISE FARE CLEANING")
    print("=" * 60)
    print(f"Route: {origin} → {destination}")
    print("=" * 60)

    raw_file = get_raw_file(origin, destination)
    raw_records = load_fares(raw_file)
    cleaned_records = clean_fares(raw_records)

    save_fares(
        cleaned_records,
        origin,
        destination
    )


if __name__ == "__main__":
    main()
