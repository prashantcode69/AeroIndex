import json
import sys
from pathlib import Path
from datetime import datetime, timezone

from mailer import send_email

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


BASE_DIR = Path(__file__).resolve().parent.parent

ALERTS_FILE = BASE_DIR / "data" / "alerts.json"


def get_args():
    """
    Example:
    python alert_checker.py DEL BOM
    """

    if len(sys.argv) >= 3:
        origin = sys.argv[1].upper()
        destination = sys.argv[2].upper()
    else:
        origin = "DEL"
        destination = "BOM"

    return origin, destination


def get_route_cleaned_file(origin, destination):
    return (
        BASE_DIR
        / "data"
        / "routes"
        / f"{origin}_{destination}"
        / "flights_cleaned.json"
    )


def load_json(path, default):
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return default


def save_alerts(alerts):
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with ALERTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(alerts, file, indent=2, ensure_ascii=False)


def current_lowest_fare(origin, destination):
    records = load_json(
        get_route_cleaned_file(origin, destination),
        []
    )

    fares = [
        record["fare"]
        for record in records
        if isinstance(record.get("fare"), (int, float))
        and record["fare"] > 0
    ]

    return min(fares) if fares else None


def main():
    origin, destination = get_args()

    print("\n" + "=" * 60)
    print("PRICE ALERT CHECK")
    print("=" * 60)
    print(f"Route: {origin} → {destination}")
    print("=" * 60)

    lowest_fare = current_lowest_fare(origin, destination)

    if lowest_fare is None:
        print("No fare data available yet - skipping alert check.")
        return

    print(f"Current lowest fare: ₹{lowest_fare:,.2f}")

    alerts = load_json(ALERTS_FILE, [])
    changed = False
    matched = 0

    for alert in alerts:
        if alert.get("notified"):
            continue

        if (
            alert.get("origin") != origin
            or alert.get("destination") != destination
        ):
            continue

        target_price = alert.get("targetPrice")

        if not isinstance(target_price, (int, float)):
            continue

        if lowest_fare > target_price:
            continue

        matched += 1

        sent = send_email(
            alert["email"],
            f"AeroIndex: {origin} → {destination} fare dropped to "
            f"₹{lowest_fare:,.0f}",
            (
                f"Good news! The {origin} → {destination} fare has "
                f"dropped to ₹{lowest_fare:,.0f}, which meets your "
                f"target of ₹{target_price:,.0f}.\n\n"
                "- AeroIndex"
            )
        )

        if sent:
            alert["notified"] = True
            alert["notifiedAt"] = datetime.now(timezone.utc).isoformat()
            changed = True
        else:
            print(
                f"(Alert for {alert['email']} matched but email was not "
                "sent - leaving it active to retry on the next refresh.)"
            )

    if changed:
        save_alerts(alerts)

    print(f"Alerts matched: {matched}")


if __name__ == "__main__":
    main()
