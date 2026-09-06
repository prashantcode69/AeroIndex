import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


BASE_DIR = Path(__file__).resolve().parent

# Demo ke liye jo routes roz refresh karne hain - list edit karke
# apne demo routes daal sakte ho.
DEMO_ROUTES = [
    ("DEL", "BOM"),
    ("DEL", "GOI"),
    ("DEL", "HYD"),
    ("BOM", "BLR"),
    ("DEL", "MAA"),
    ("DEL", "CCU"),
    ("BLR", "HYD"),
    ("DEL", "AMD"),
]


def main():
    python = sys.executable

    print("\n" + "=" * 60)
    print("AEROINDEX DAILY REFRESH")
    print(f"Routes: {DEMO_ROUTES}")
    print("=" * 60)

    for origin, destination in DEMO_ROUTES:
        print(f"\n--- Refreshing {origin} -> {destination} ---")

        result = subprocess.run(
            [python, "run_pipeline.py", origin, destination],
            cwd=BASE_DIR,
            check=False,
        )

        if result.returncode != 0:
            print(
                f"⚠️ Refresh failed for {origin} -> {destination} "
                f"(exit code {result.returncode})"
            )
        else:
            print(f"✅ Refreshed {origin} -> {destination}")

    print("\nDaily refresh finished.")


if __name__ == "__main__":
    main()
