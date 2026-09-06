import json
import re
import sys
from pathlib import Path
from datetime import date, timedelta, datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


SOURCE = "Google Flights"

AIRLINES = [
    "IndiGo",
    "Air India",
    "Air India Express",
    "Akasa Air",
    "SpiceJet",
    "Vistara",
    "Alliance Air",
]

FARE_PATTERN = re.compile(r"₹\s?([\d,]+)")


def get_args():
    """
    Example:
    python extract_google_fares.py DEL BOM 15
    """

    if len(sys.argv) >= 4:
        origin = sys.argv[1].upper()
        destination = sys.argv[2].upper()
        booking_window = int(sys.argv[3])
    else:
        origin = "DEL"
        destination = "BOM"
        booking_window = 15

    return origin, destination, booking_window


def get_text_path(booking_window):
    return Path(f"data/raw/google_flights_results_{booking_window}.txt")


def get_raw_fares_file(origin, destination, booking_window):
    """
    Window-specific output - alag alag booking windows ab parallel
    mein scrape/extract hote hain, isliye har window apni alag file
    mein likhta hai (read-modify-write race avoid karne ke liye).

    Example:
    data/raw/DEL_BOM_fares_raw_15.json
    """

    path = (
        Path("data/raw")
        / f"{origin}_{destination}_fares_raw_{booking_window}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)

    return path


def extract_records(text, origin, destination, booking_window, departure_date):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    records = []

    for i, line in enumerate(lines):
        if line not in AIRLINES:
            continue

        # Nearby lines mein fare search karo
        nearby = lines[i:i + 8]
        fare = None

        for nearby_line in nearby:
            match = FARE_PATTERN.search(nearby_line)
            if match:
                fare = int(match.group(1).replace(",", ""))
                break

        if fare is None:
            continue

        records.append({
            "source": SOURCE,
            "airline": line,
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date.isoformat(),
            "booking_window": booking_window,
            "fare": fare,
            "currency": "INR",
            "collected_at": datetime.now(timezone.utc).isoformat(),
        })

    return records


def main():
    origin, destination, booking_window = get_args()

    departure_date = date.today() + timedelta(days=booking_window)

    text = get_text_path(booking_window).read_text(encoding="utf-8")

    new_records = extract_records(
        text,
        origin,
        destination,
        booking_window,
        departure_date,
    )

    output_path = get_raw_fares_file(origin, destination, booking_window)

    output_path.write_text(
        json.dumps(new_records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Extracted records (window {booking_window}d): {len(new_records)}")
    print(f"Saved to: {output_path}")

    for record in new_records:
        print(
            record["airline"],
            "₹" + f'{record["fare"]:,}',
            f'(window: {record["booking_window"]}d)'
        )


if __name__ == "__main__":
    main()
