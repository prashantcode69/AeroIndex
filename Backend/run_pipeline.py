import concurrent.futures
import json
import subprocess
import sys
from pathlib import Path

# Windows par jab stdout ek console na ho (Task Scheduler, piped
# output, etc.), default encoding cp1252 hoti hai jo ₹ aur emoji
# par crash kar deti hai. UTF-8 force karna safe hai.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


BASE_DIR = Path(__file__).resolve().parent

STATUS_FILE = BASE_DIR / "data" / "pipeline_status.json"

# Alag alag booking windows jo scrape kiye jaate hain, taaki
# "best time to book" asli data se calculate ho sake, hardcoded
# string se nahi. Sabhi windows PARALLEL mein scrape hote hain
# (alag process, alag headless browser) - sequential karne mein
# ek naye route ke liye 60-90+ seconds lagte the, parallel mein
# ye ~sabse slow window jitna time lagta hai (~15-20s).
BOOKING_WINDOWS = [7, 15, 30, 45]


def write_status(origin, destination, stage, windows_completed=None, total_windows=None):
    """
    Shared status file jo Flask (/api/refresh-status) padhta hai, taaki
    frontend ko asli progress dikha sake - fake spinner nahi, genuinely
    kitne booking windows scrape ho chuke hain wo.

    Temp file + atomic replace - taaki Flask kabhi aadha-likha JSON na
    padhe.
    """

    status = {
        "origin": origin,
        "destination": destination,
        "stage": stage,
        "windowsCompleted": windows_completed,
        "totalWindows": total_windows,
    }

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    tmp_file = STATUS_FILE.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(status), encoding="utf-8")
    tmp_file.replace(STATUS_FILE)


def run_step(title, command):
    """
    Step chalata hai aur failure par poora process exit kar deta hai.
    Sequential (non-parallel) steps ke liye - agar ye kisi worker
    thread ke andar call kiya jaaye toh sys.exit sirf us thread ko
    rokega, poore process ko nahi, isliye parallel steps ke liye
    run_step_soft use karo.
    """

    ok = run_step_soft(title, command)

    if not ok:
        sys.exit(1)


def run_step_soft(title, command):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    result = subprocess.run(
        command,
        cwd=BASE_DIR,
        check=False
    )

    if result.returncode != 0:
        print(f"\n❌ Step failed: {title}")
        return False

    print(f"✅ Completed: {title}")
    return True


def scrape_window(python, origin, destination, window):
    scrape_ok = run_step_soft(
        f"Google Flights Scraper (window: {window}d)",
        [
            python,
            "scraper/search_flights.py",
            origin,
            destination,
            str(window)
        ]
    )

    if not scrape_ok:
        return False

    return run_step_soft(
        f"Extract Google Flight Fares (window: {window}d)",
        [
            python,
            "scraper/extract_google_fares.py",
            origin,
            destination,
            str(window)
        ]
    )


def main():
    python = sys.executable

    # Command se route receive hoga
    # Example:
    # python run_pipeline.py DEL BLR

    if len(sys.argv) >= 3:
        origin = sys.argv[1].upper()
        destination = sys.argv[2].upper()
    else:
        origin = "DEL"
        destination = "BOM"

    print("\n" + "=" * 60)
    print("AEROINDEX ROUTE PIPELINE")
    print("=" * 60)
    print(f"Selected route: {origin} → {destination}")
    print(f"Booking windows (parallel): {BOOKING_WINDOWS}")
    print("=" * 60)

    total_windows = len(BOOKING_WINDOWS)
    windows_completed = 0

    write_status(origin, destination, "scraping", windows_completed, total_windows)

    results = {}

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=total_windows
    ) as executor:
        futures = {
            executor.submit(
                scrape_window, python, origin, destination, window
            ): window
            for window in BOOKING_WINDOWS
        }

        for future in concurrent.futures.as_completed(futures):
            window = futures[future]
            results[window] = future.result()
            windows_completed += 1

            write_status(
                origin, destination, "scraping",
                windows_completed, total_windows
            )

    failed_windows = sorted(
        window for window, ok in results.items() if not ok
    )

    if failed_windows:
        print(
            f"\n❌ Scraping failed for booking windows: {failed_windows}"
        )
        write_status(origin, destination, "failed")
        sys.exit(1)

    write_status(origin, destination, "analyzing")

    run_step(
        "3. Deduplicate Google Fares",
        [
            python,
            "scraper/deduplicate_google_fares.py",
            origin,
            destination
        ]
    )

    run_step(
        "4. Clean Fare Data",
        [
            python,
            "pipeline/cleaner.py",
            origin,
            destination
        ]
    )

    write_status(origin, destination, "computing")

    run_step(
        "5. Save Historical Data",
        [
            python,
            "pipeline/history_saver.py",
            origin,
            destination
        ]
    )

    run_step(
        "6. Check Price Alerts",
        [
            python,
            "pipeline/alert_checker.py",
            origin,
            destination
        ]
    )

    write_status(origin, destination, "done")

    print("\n" + "=" * 60)
    print("🎉 COMPLETE PIPELINE FINISHED SUCCESSFULLY")
    print(f"Route completed: {origin} → {destination}")
    print("=" * 60)


if __name__ == "__main__":
    main()
