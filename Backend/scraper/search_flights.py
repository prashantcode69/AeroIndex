from datetime import date, timedelta
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# Default route/window agar koi provide na kiya jaye
DEFAULT_ORIGIN = "DEL"
DEFAULT_DESTINATION = "BOM"
DEFAULT_BOOKING_WINDOW = 15


def get_route():
    """
    Command line se airport codes aur booking window leta hai.

    Example:
    python search_flights.py DEL BLR 15
    """

    if len(sys.argv) >= 3:
        origin = sys.argv[1].upper()
        destination = sys.argv[2].upper()
    else:
        origin = DEFAULT_ORIGIN
        destination = DEFAULT_DESTINATION

    if len(sys.argv) >= 4:
        booking_window = int(sys.argv[3])
    else:
        booking_window = DEFAULT_BOOKING_WINDOW

    return origin, destination, booking_window


def main():
    origin, destination, booking_window = get_route()

    departure_date = date.today() + timedelta(days=booking_window)

    search_url = (
        "https://www.google.com/travel/flights"
        f"?q=Flights%20from%20{origin}%20to%20{destination}"
        f"%20on%20{departure_date.isoformat()}"
    )

    print("\n" + "=" * 60)
    print("GOOGLE FLIGHTS SEARCH")
    print("=" * 60)
    print(f"Origin: {origin}")
    print(f"Destination: {destination}")
    print(f"Booking window: {booking_window} days ahead")
    print(f"Departure date: {departure_date}")
    print(f"Search URL: {search_url}")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1000,
            }
        )

        try:
            page.goto(
                search_url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            # Google Flights ko results load karne ka time
            page.wait_for_timeout(10000)

            print("Title:", page.title())
            print("URL:", page.url)

            text = page.locator("body").inner_text()

            # Window-specific file - alag alag booking windows ab
            # parallel mein scrape hote hain, isliye ek shared scratch
            # file use nahi kar sakte (overwrite race ho jaayega).
            output_path = Path(
                f"data/raw/google_flights_results_{booking_window}.txt"
            )

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            output_path.write_text(
                text,
                encoding="utf-8",
            )

            print("\nResults text saved.")
            print(
                f"Route saved: {origin} -> {destination} "
                f"(window: {booking_window}d)"
            )
            print("\nFirst 3000 characters:\n")
            print(text[:3000])

        except Exception as error:
            print(
                "\n❌ Google Flights scraping error:",
                error
            )
            sys.exit(1)

        finally:
            browser.close()
            print("\nBrowser closed.")


if __name__ == "__main__":
    main()
