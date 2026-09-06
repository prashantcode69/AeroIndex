from flask import Flask, jsonify, request
from flask_cors import CORS
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import quote
import json
import re
import statistics
import subprocess
import sys
import threading
import time
import uuid


app = Flask(__name__)
CORS(app)


# --------------------------------------------------
# PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_FILE = (
    BASE_DIR
    / "data"
    / "cleaned"
    / "flights_cleaned.json"
)

HISTORY_FILE = (
    BASE_DIR
    / "data"
    / "history"
    / "airfare_history.json"
)

PIPELINE_STATUS_FILE = (
    BASE_DIR
    / "data"
    / "pipeline_status.json"
)

# Kitni der tak collected data ko "fresh" mana jaaye, taaki live
# demo ke waqt scraping par depend na karna pade agar route
# recently already refresh ho chuka ho.
CACHE_TTL_HOURS = 24


# --------------------------------------------------
# PIPELINE STATUS
# --------------------------------------------------

pipeline_running = False
pipeline_lock = threading.Lock()

current_pipeline_route = {
    "from": "",
    "to": ""
}


def run_refresh_pipeline(origin, destination):
    global pipeline_running

    try:
        print("\n" + "=" * 60)
        print("STARTING FRESH AIRFARE PIPELINE")
        print("=" * 60)
        print(f"Route: {origin} → {destination}")
        print("=" * 60)

        python_path = sys.executable

        result = subprocess.run(
            [
                python_path,
                "run_pipeline.py",
                origin,
                destination
            ],
            cwd=BASE_DIR,
            check=False
        )

        if result.returncode == 0:
            print(
                f"Fresh pipeline completed successfully "
                f"for {origin} → {destination}"
            )
        else:
            print(
                f"Pipeline failed with exit code: "
                f"{result.returncode}"
            )

    except Exception as error:
        print(f"Pipeline error: {error}")

    finally:
        pipeline_running = False
        current_pipeline_route["from"] = ""
        current_pipeline_route["to"] = ""

        print("Pipeline status: stopped")


# --------------------------------------------------
# CITY NORMALIZATION
# --------------------------------------------------

CITY_ALIASES = {
    "delhi": "DEL",
    "new delhi": "DEL",
    "del": "DEL",

    "mumbai": "BOM",
    "bombay": "BOM",
    "bom": "BOM",

    "bangalore": "BLR",
    "bengaluru": "BLR",
    "blr": "BLR",

    "hyderabad": "HYD",
    "hyd": "HYD",

    "chennai": "MAA",
    "madras": "MAA",
    "maa": "MAA",

    "kolkata": "CCU",
    "calcutta": "CCU",
    "ccu": "CCU",

    "pune": "PNQ",
    "pnq": "PNQ",

    "goa": "GOI",
    "goi": "GOI",

    "ahmedabad": "AMD",
    "amd": "AMD",

    "jaipur": "JAI",
    "jai": "JAI",

    "lucknow": "LKO",
    "lko": "LKO",

    "patna": "PAT",
    "pat": "PAT",

    "kochi": "COK",
    "cochin": "COK",
    "cok": "COK",

    "guwahati": "GAU",
    "gau": "GAU",

    "chandigarh": "IXC",
    "ixc": "IXC",

    "srinagar": "SXR",
    "sxr": "SXR",

    "bhubaneswar": "BBI",
    "bbi": "BBI",

    "indore": "IDR",
    "idr": "IDR",

    "nagpur": "NAG",
    "nag": "NAG",

    "varanasi": "VNS",
    "banaras": "VNS",
    "vns": "VNS",

    "amritsar": "ATQ",
    "atq": "ATQ",

    "raipur": "RPR",
    "rpr": "RPR",

    "ranchi": "IXR",
    "ixr": "IXR",

    "coimbatore": "CJB",
    "cjb": "CJB",

    "madurai": "IXM",
    "ixm": "IXM",

    "visakhapatnam": "VTZ",
    "vizag": "VTZ",
    "vtz": "VTZ",

    "trivandrum": "TRV",
    "thiruvananthapuram": "TRV",
    "trv": "TRV",

    "mangalore": "IXE",
    "ixe": "IXE",

    "nashik": "ISK",
    "isk": "ISK",

    "surat": "STV",
    "stv": "STV",

    "vadodara": "BDQ",
    "baroda": "BDQ",
    "bdq": "BDQ",

    "bhopal": "BHO",
    "bho": "BHO",

    "dehradun": "DED",
    "ded": "DED",

    "port blair": "IXZ",
    "ixz": "IXZ",

    "agartala": "IXA",
    "ixa": "IXA",

    "imphal": "IMF",
    "imf": "IMF",

    "dibrugarh": "DIB",
    "dib": "DIB",

    "jodhpur": "JDH",
    "jdh": "JDH",

    "udaipur": "UDR",
    "udr": "UDR",

    "bagdogra": "IXB",
    "ixb": "IXB",

    "silchar": "IXS",
    "ixs": "IXS",

    "jammu": "IXJ",
    "ixj": "IXJ",

    "leh": "IXL",
    "ixl": "IXL",

    "rajkot": "RAJ",
    "raj": "RAJ",

    "aurangabad": "IXU",
    "ixu": "IXU",

    "tirupati": "TIR",
    "tir": "TIR",

    "vijayawada": "VGA",
    "vga": "VGA",

    "bhavnagar": "BHU",
    "bhu": "BHU",

    "jabalpur": "JLR",
    "jlr": "JLR",

    "gaya": "GAY",
    "gay": "GAY",

    "durgapur": "RDP",
    "rdp": "RDP",

    "belgaum": "IXG",
    "ixg": "IXG",

    "hubli": "HBX",
    "hbx": "HBX",

    "mysore": "MYQ",
    "mysuru": "MYQ",
    "myq": "MYQ",

    "pondicherry": "PNY",
    "puducherry": "PNY",
    "pny": "PNY",
}


CITY_NAMES = {
    "DEL": "Delhi",
    "BOM": "Mumbai",
    "BLR": "Bengaluru",
    "HYD": "Hyderabad",
    "MAA": "Chennai",
    "CCU": "Kolkata",
    "PNQ": "Pune",
    "GOI": "Goa",
    "AMD": "Ahmedabad",
    "JAI": "Jaipur",
    "LKO": "Lucknow",
    "PAT": "Patna",
    "COK": "Kochi",
    "GAU": "Guwahati",
    "IXC": "Chandigarh",
    "SXR": "Srinagar",
    "BBI": "Bhubaneswar",
    "IDR": "Indore",
    "NAG": "Nagpur",
    "VNS": "Varanasi",
    "ATQ": "Amritsar",
    "RPR": "Raipur",
    "IXR": "Ranchi",
    "CJB": "Coimbatore",
    "IXM": "Madurai",
    "VTZ": "Visakhapatnam",
    "TRV": "Trivandrum",
    "IXE": "Mangalore",
    "ISK": "Nashik",
    "STV": "Surat",
    "BDQ": "Vadodara",
    "BHO": "Bhopal",
    "DED": "Dehradun",
    "IXZ": "Port Blair",
    "IXA": "Agartala",
    "IMF": "Imphal",
    "DIB": "Dibrugarh",
    "JDH": "Jodhpur",
    "UDR": "Udaipur",
    "IXB": "Bagdogra",
    "IXS": "Silchar",
    "IXJ": "Jammu",
    "IXL": "Leh",
    "RAJ": "Rajkot",
    "IXU": "Aurangabad",
    "TIR": "Tirupati",
    "VGA": "Vijayawada",
    "BHU": "Bhavnagar",
    "JLR": "Jabalpur",
    "GAY": "Gaya",
    "RDP": "Durgapur",
    "IXG": "Belgaum",
    "HBX": "Hubli",
    "MYQ": "Mysuru",
    "PNY": "Puducherry",
}


# --------------------------------------------------
# AIRLINE CODES
# --------------------------------------------------

AIRLINE_CODES = {
    "IndiGo": "6E",
    "Air India": "AI",
    "Air India Express": "IX",
    "Akasa Air": "QP",
    "Vistara": "UK",
    "SpiceJet": "SG",
    "Go First": "G8",
    "Alliance Air": "9I",
}


# --------------------------------------------------
# ROUTE DISTANCES
# --------------------------------------------------

ROUTE_DISTANCES = {
    ("DEL", "BOM"): "1,148 km",
    ("BOM", "DEL"): "1,148 km",

    ("DEL", "BLR"): "1,740 km",
    ("BLR", "DEL"): "1,740 km",

    ("DEL", "HYD"): "1,260 km",
    ("HYD", "DEL"): "1,260 km",

    ("DEL", "MAA"): "1,760 km",
    ("MAA", "DEL"): "1,760 km",

    ("DEL", "CCU"): "1,300 km",
    ("CCU", "DEL"): "1,300 km",

    ("DEL", "GOI"): "1,510 km",
    ("GOI", "DEL"): "1,510 km",

    ("DEL", "AMD"): "755 km",
    ("AMD", "DEL"): "755 km",

    ("DEL", "PNQ"): "1,175 km",
    ("PNQ", "DEL"): "1,175 km",

    ("DEL", "JAI"): "235 km",
    ("JAI", "DEL"): "235 km",

    ("DEL", "LKO"): "425 km",
    ("LKO", "DEL"): "425 km",

    ("DEL", "PAT"): "850 km",
    ("PAT", "DEL"): "850 km",

    ("DEL", "COK"): "2,080 km",
    ("COK", "DEL"): "2,080 km",

    ("DEL", "GAU"): "1,450 km",
    ("GAU", "DEL"): "1,450 km",

    ("DEL", "IXC"): "245 km",
    ("IXC", "DEL"): "245 km",

    ("DEL", "SXR"): "645 km",
    ("SXR", "DEL"): "645 km",

    ("BOM", "BLR"): "840 km",
    ("BLR", "BOM"): "840 km",

    ("BOM", "HYD"): "620 km",
    ("HYD", "BOM"): "620 km",

    ("BOM", "MAA"): "1,030 km",
    ("MAA", "BOM"): "1,030 km",

    ("BOM", "GOI"): "430 km",
    ("GOI", "BOM"): "430 km",

    ("BLR", "HYD"): "500 km",
    ("HYD", "BLR"): "500 km",

    ("BLR", "MAA"): "290 km",
    ("MAA", "BLR"): "290 km",

    ("BLR", "GOI"): "480 km",
    ("GOI", "BLR"): "480 km",

    ("BLR", "CCU"): "1,560 km",
    ("CCU", "BLR"): "1,560 km",

    ("HYD", "MAA"): "520 km",
    ("MAA", "HYD"): "520 km",

    ("HYD", "GOI"): "530 km",
    ("GOI", "HYD"): "530 km",
}


# --------------------------------------------------
# FILE HELPERS
# --------------------------------------------------

def load_json_file(file_path, default):
    if not file_path.exists():
        return default

    try:
        with file_path.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except Exception as error:
        print(
            f"Error loading {file_path}: {error}"
        )
        return default


def get_route_file(origin, destination):
    return (
        BASE_DIR
        / "data"
        / "routes"
        / f"{origin}_{destination}"
        / "flights_cleaned.json"
    )


def get_route_history_file(origin, destination):
    return (
        BASE_DIR
        / "data"
        / "routes"
        / f"{origin}_{destination}"
        / "history.json"
    )


def route_data_age_hours(origin, destination):
    """
    Route ki cleaned fare file kitni purani hai (hours mein).
    File missing ho toh None return karta hai.
    """

    route_file = get_route_file(
        origin,
        destination
    )

    if not route_file.exists():
        return None

    age_seconds = time.time() - route_file.stat().st_mtime

    return age_seconds / 3600


def load_fares(origin, destination):
    route_file = get_route_file(
        origin,
        destination
    )

    data = load_json_file(
        route_file,
        []
    )

    if isinstance(data, list) and data:
        return data

    # Reverse route fallback
    reverse_file = get_route_file(
        destination,
        origin
    )

    reverse_data = load_json_file(
        reverse_file,
        []
    )

    if isinstance(reverse_data, list):
        return reverse_data

    # Old common file fallback
    old_data = load_json_file(
        DATA_FILE,
        []
    )

    if isinstance(old_data, list):
        return old_data

    return []


def load_history(origin, destination):
    route_history_file = get_route_history_file(
        origin,
        destination
    )

    data = load_json_file(
        route_history_file,
        []
    )

    if isinstance(data, list) and data:
        return data

    reverse_history_file = get_route_history_file(
        destination,
        origin
    )

    reverse_data = load_json_file(
        reverse_history_file,
        []
    )

    if isinstance(reverse_data, list):
        return reverse_data

    old_data = load_json_file(
        HISTORY_FILE,
        []
    )

    if isinstance(old_data, list):
        return old_data

    return []


# --------------------------------------------------
# CITY HELPERS
# --------------------------------------------------

def normalize_city(value):
    value = str(
        value or ""
    ).strip().lower()

    if not value:
        return ""

    return CITY_ALIASES.get(
        value,
        value.upper()
    )


def city_name(code):
    if code in CITY_NAMES:
        return CITY_NAMES[code]

    # Unknown city (not in our curated list) - agar 3-letter IATA
    # code jaisa dikhta hai toh as-is rakho, warna typed city name
    # ho sakta hai, toh nicely title-case kar do ("KANPUR" -> "Kanpur")
    # raw uppercase dikhane ke bajaye.
    if len(code) == 3 and code.isalpha():
        return code

    return code.title()


def route_distance(origin, destination):
    return ROUTE_DISTANCES.get(
        (origin, destination),
        "Distance unavailable"
    )


# --------------------------------------------------
# BOOKING URL
# --------------------------------------------------

def booking_url(origin, destination):
    origin_name = quote(
        city_name(origin)
    )

    destination_name = quote(
        city_name(destination)
    )

    return (
        "https://www.google.com/travel/flights?"
        f"q=Flights%20from%20{origin_name}%20to%20"
        f"{destination_name}"
    )


# --------------------------------------------------
# NUMBER HELPERS
# --------------------------------------------------

def safe_float(value):
    try:
        number = float(value)

        if number > 0:
            return number

        return 0.0

    except (
        TypeError,
        ValueError
    ):
        return 0.0


def percentage_difference(value, reference):
    if reference <= 0:
        return 0.0

    return round(
        (
            (value - reference)
            / reference
        ) * 100,
        1
    )


# --------------------------------------------------
# HOME API
# --------------------------------------------------

@app.get("/")
def home():
    return jsonify({
        "app": "AeroIndex API",
        "status": "running",
        "version": "5.0"
    })


# --------------------------------------------------
# CITIES API (for search autocomplete)
# --------------------------------------------------

@app.get("/api/cities")
def cities():
    city_list = sorted(
        (
            {"code": code, "name": name}
            for code, name in CITY_NAMES.items()
        ),
        key=lambda item: item["name"]
    )

    return jsonify({"cities": city_list})


# --------------------------------------------------
# REFRESH API
# --------------------------------------------------

@app.post("/api/refresh")
def refresh_pipeline():
    global pipeline_running

    body = request.get_json(
        silent=True
    ) or {}

    origin = normalize_city(
        body.get("from")
        or request.args.get("from")
        or "DEL"
    )

    destination = normalize_city(
        body.get("to")
        or request.args.get("to")
        or "BOM"
    )

    if not origin or not destination:
        return jsonify({
            "error": "Both from and to cities are required."
        }), 400

    if origin == destination:
        return jsonify({
            "error": "From and to cities cannot be same."
        }), 400

    force_refresh = bool(
        body.get("force")
        or request.args.get("force")
    )

    if not force_refresh:
        data_age_hours = route_data_age_hours(
            origin,
            destination
        )

        if (
            data_age_hours is not None
            and data_age_hours < CACHE_TTL_HOURS
        ):
            return jsonify({
                "status": "cached",
                "message": (
                    "Recently collected data is already "
                    "available for this route."
                ),
                "from": origin,
                "to": destination,
                "ageHours": round(data_age_hours, 2)
            }), 200

    with pipeline_lock:
        if pipeline_running:
            return jsonify({
                "status": "already_running",
                "message": (
                    "Fresh airfare data is already being collected."
                ),
                "from": origin,
                "to": destination
            }), 202

        pipeline_running = True

        current_pipeline_route["from"] = origin
        current_pipeline_route["to"] = destination

    thread = threading.Thread(
        target=run_refresh_pipeline,
        args=(
            origin,
            destination
        ),
        daemon=True
    )

    thread.start()

    return jsonify({
        "status": "started",
        "message": (
            "Fresh airfare data collection has started."
        ),
        "from": origin,
        "to": destination
    }), 202


@app.get("/api/refresh-status")
def refresh_status():
    response = {
        "running": pipeline_running,
        "from": current_pipeline_route["from"],
        "to": current_pipeline_route["to"]
    }

    if pipeline_running:
        status = load_json_file(PIPELINE_STATUS_FILE, {})

        # Sirf tabhi include karo jab ye status genuinely isi route ke
        # liye ho - purane run ka stale stage kabhi na dikhe.
        if (
            status.get("origin") == current_pipeline_route["from"]
            and status.get("destination") == current_pipeline_route["to"]
        ):
            response["stage"] = status.get("stage")
            response["windowsCompleted"] = status.get("windowsCompleted")
            response["totalWindows"] = status.get("totalWindows")

    return jsonify(response)


# --------------------------------------------------
# TREND / "BOOK NOW VS WAIT" SIGNAL
# --------------------------------------------------

TREND_CHANGE_THRESHOLD_PERCENT = 2.0


def compute_trend(history):
    """
    Route ke saved daily history se trend nikalta hai - fares
    rising hain, falling hain, ya stable hain - aur uske hisaab
    se "book now vs wait" recommendation deta hai.

    Kam se kam 2 din ka real history chahiye, warna abhi ke liye
    "insufficient_data" return hota hai (naya route ya abhi tak
    sirf ek din ka data collect hua ho).
    """

    if len(history) < 2:
        return {
            "direction": "insufficient_data",
            "changePercent": None,
            "recommendation": (
                "Not enough historical data yet to detect a "
                "price trend for this route - check back after "
                "a few more days of data collection."
            )
        }

    previous_average = history[-2]["avg"]
    latest_average = history[-1]["avg"]

    change_percent = percentage_difference(
        latest_average,
        previous_average
    )

    if change_percent > TREND_CHANGE_THRESHOLD_PERCENT:
        direction = "rising"
        recommendation = (
            f"Fares have risen {change_percent}% since the last "
            "check. Prices are trending up - booking now is "
            "likely cheaper than waiting."
        )
    elif change_percent < -TREND_CHANGE_THRESHOLD_PERCENT:
        direction = "falling"
        recommendation = (
            f"Fares have dropped {abs(change_percent)}% since "
            "the last check. Prices are trending down - it may "
            "be worth waiting a little longer before booking."
        )
    else:
        direction = "stable"
        recommendation = (
            "Fares have been broadly stable recently - book "
            "whenever suits you."
        )

    return {
        "direction": direction,
        "changePercent": change_percent,
        "recommendation": recommendation
    }


# --------------------------------------------------
# AIRFARE COMPUTATION (shared by /api/airfare and
# /api/market-overview so both use the exact same logic)
# --------------------------------------------------

def build_airfare_data(origin, destination):
    """
    Route ke liye poora computed airfare payload banata hai.

    Return: (data_dict, None) success par, ya
            (None, (error_dict, status_code)) failure par.
    """

    all_fares = load_fares(
        origin,
        destination
    )

    if not all_fares:
        return None, ({
            "error": (
                f"No fare data found for "
                f"{city_name(origin)} to "
                f"{city_name(destination)}."
            ),
            "from": city_name(origin),
            "to": city_name(destination)
        }, 404)

    route_fares = [
        item
        for item in all_fares
        if (
            normalize_city(item.get("origin"))
            == origin
            and
            normalize_city(item.get("destination"))
            == destination
        )
    ]

    is_reverse_route = False

    if not route_fares:
        route_fares = [
            item
            for item in all_fares
            if (
                normalize_city(item.get("origin"))
                == destination
                and
                normalize_city(item.get("destination"))
                == origin
            )
        ]

        if route_fares:
            is_reverse_route = True

    # Route folder ke data mein origin/destination missing
    # ho toh us route folder ke saare fares use honge.
    if not route_fares:
        route_fares = all_fares

    valid_records = []

    for item in route_fares:
        fare = safe_float(
            item.get("fare")
        )

        if fare <= 0:
            continue

        valid_records.append({
            **item,
            "fare": fare
        })

    if not valid_records:
        return None, ({
            "error": "Fare values are unavailable for this route."
        }, 404)

    # --------------------------------------------------
    # BEST BOOKING WINDOW
    # --------------------------------------------------
    # Records multiple booking windows (7/15/30/45 din pehle)
    # collect karte hain. Sabse sasta average jis window par
    # milta hai, wahi "best time to book" hai - hardcoded
    # string ki jagah asli data se nikala gaya.

    window_groups = defaultdict(list)

    for item in valid_records:
        window = item.get("booking_window")

        if isinstance(window, (int, float)):
            window_groups[int(window)].append(item["fare"])

    booking_window_breakdown = []
    best_window = None
    best_window_average = None

    for window in sorted(window_groups.keys()):
        fares_for_window = window_groups[window]
        window_average = round(
            statistics.mean(fares_for_window),
            2
        )

        booking_window_breakdown.append({
            "bookingWindow": window,
            "averageFare": window_average,
            "observations": len(fares_for_window)
        })

        if (
            best_window_average is None
            or window_average < best_window_average
        ):
            best_window_average = window_average
            best_window = window

    if best_window is not None:
        best_booking_window = f"Around {best_window} days before departure"
    else:
        best_booking_window = "Not enough data yet"

    REFERENCE_BOOKING_WINDOW = 15

    reference_records = [
        item
        for item in valid_records
        if item.get("booking_window") == REFERENCE_BOOKING_WINDOW
    ]

    # Reference window ka data abhi tak collect nahi hua toh
    # saare windows ke combined data se hi dashboard dikhao.
    if not reference_records:
        reference_records = valid_records

    fare_values = [
        item["fare"]
        for item in reference_records
    ]

    current_average = round(
        statistics.mean(fare_values),
        2
    )

    current_lowest = round(
        min(fare_values),
        2
    )

    current_highest = round(
        max(fare_values),
        2
    )

    base_fare = current_lowest if current_lowest > 0 else current_average

    index_value = round(
        (
            current_average
            / base_fare
        ) * 100,
        2
    )

    # --------------------------------------------------
    # AIRLINE DATA
    # --------------------------------------------------

    airline_groups = defaultdict(list)

    for item in reference_records:
        airline = (
            item.get("airline")
            or "Unknown airline"
        )

        airline_groups[airline].append(
            item["fare"]
        )

    airline_average_values = {
        airline: statistics.mean(fares)
        for airline, fares
        in airline_groups.items()
    }

    cheapest_airline_average = min(
        airline_average_values.values()
    )

    airline_data = []

    for airline, fares in airline_groups.items():
        airline_lowest = round(
            min(fares),
            2
        )

        airline_average = round(
            statistics.mean(fares),
            2
        )

        difference_percent = percentage_difference(
            airline_average,
            current_average
        )

        is_best_value = (
            airline_average
            == cheapest_airline_average
        )

        if is_best_value:
            change_text = "Best value"
        elif difference_percent > 0:
            change_text = f"+{difference_percent}%"
        else:
            change_text = f"{difference_percent}%"

        airline_data.append({
            "name": airline,
            "code": AIRLINE_CODES.get(
                airline,
                airline[:2].upper()
            ),
            "lowestFare": airline_lowest,
            "averageFare": airline_average,
            "fare": airline_lowest,
            "change": change_text,
            "differencePercent": difference_percent,
            "observations": len(fares)
        })

    airline_data.sort(
        key=lambda item: item["lowestFare"]
    )

    # --------------------------------------------------
    # HISTORY
    # --------------------------------------------------

    saved_history = load_history(
        origin,
        destination
    )

    history = []

    for item in saved_history:
        average_fare = safe_float(
            item.get("averageFare")
        )

        lowest_fare = safe_float(
            item.get("lowestFare")
        )

        highest_fare = safe_float(
            item.get("highestFare")
        )

        if average_fare <= 0:
            continue

        history.append({
            "name": item.get(
                "date",
                "Unknown"
            ),
            "avg": round(
                average_fare,
                2
            ),
            "low": round(
                lowest_fare,
                2
            ),
            "high": round(
                highest_fare,
                2
            ),
            "observations": item.get(
                "observations",
                0
            )
        })

    if not history:
        history = [{
            "name": "Latest",
            "avg": current_average,
            "low": current_lowest,
            "high": current_highest,
            "observations": len(reference_records)
        }]

    trend = compute_trend(history)

    return {
        "index": index_value,

        "averageFare": current_average,
        "lowestFare": current_lowest,
        "highestFare": current_highest,

        "baseFare": base_fare,
        "currency": "INR",

        "from": city_name(origin),
        "to": city_name(destination),

        "fromCode": origin,
        "toCode": destination,

        "route": (
            f"{city_name(origin)}-"
            f"{city_name(destination)}"
        ),

        "distance": route_distance(
            origin,
            destination
        ),

        "bestBookingWindow": best_booking_window,
        "bookingWindowBreakdown": booking_window_breakdown,
        "priceChange": "Live data",
        "observations": len(reference_records),
        "source": "Google Flights",
        "isReverseRoute": is_reverse_route,

        "bookingUrl": booking_url(
            origin,
            destination
        ),

        "airlines": airline_data,
        "history": history,
        "trend": trend
    }, None


@app.get("/api/airfare")
def airfare():
    origin = normalize_city(
        request.args.get("from")
    )

    destination = normalize_city(
        request.args.get("to")
    )

    if not origin or not destination:
        return jsonify({
            "error": "Both from and to cities are required."
        }), 400

    if origin == destination:
        return jsonify({
            "error": (
                "Departure and arrival cities "
                "cannot be the same."
            )
        }), 400

    data, error = build_airfare_data(origin, destination)

    if error:
        error_body, status_code = error
        return jsonify(error_body), status_code

    return jsonify(data)


# --------------------------------------------------
# MARKET OVERVIEW API
# --------------------------------------------------

def route_last_updated(origin, destination):
    route_file = get_route_file(origin, destination)

    if not route_file.exists():
        return None

    return datetime.fromtimestamp(
        route_file.stat().st_mtime,
        tz=timezone.utc
    ).isoformat()


@app.get("/api/market-overview")
def market_overview():
    routes_dir = BASE_DIR / "data" / "routes"

    entries = []

    if routes_dir.exists():
        for folder in sorted(routes_dir.iterdir()):
            if not folder.is_dir() or "_" not in folder.name:
                continue

            origin, _, destination = folder.name.partition("_")
            origin = origin.upper()
            destination = destination.upper()

            data, error = build_airfare_data(origin, destination)

            if error:
                continue

            entries.append({
                "fromCode": origin,
                "toCode": destination,
                "from": data["from"],
                "to": data["to"],
                "route": data["route"],
                "index": data["index"],
                "averageFare": data["averageFare"],
                "lowestFare": data["lowestFare"],
                "bestBookingWindow": data["bestBookingWindow"],
                "trend": data["trend"],
                "observations": data["observations"],
                "lastUpdated": route_last_updated(origin, destination)
            })

    entries.sort(key=lambda entry: entry["index"], reverse=True)

    market_average_index = (
        round(
            sum(entry["index"] for entry in entries) / len(entries),
            2
        )
        if entries
        else None
    )

    return jsonify({
        "routes": entries,
        "routeCount": len(entries),
        "marketAverageIndex": market_average_index
    })


# --------------------------------------------------
# PRICE ALERTS API
# --------------------------------------------------

ALERTS_FILE = BASE_DIR / "data" / "alerts.json"

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def load_alerts():
    data = load_json_file(ALERTS_FILE, [])
    return data if isinstance(data, list) else []


def save_alerts(alerts):
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with ALERTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(alerts, file, indent=2, ensure_ascii=False)


@app.post("/api/alerts")
def create_alert():
    body = request.get_json(silent=True) or {}

    email = str(body.get("email") or "").strip()
    origin = normalize_city(body.get("from"))
    destination = normalize_city(body.get("to"))
    target_price = safe_float(body.get("targetPrice"))

    if not EMAIL_PATTERN.match(email):
        return jsonify({
            "error": "Please enter a valid email address."
        }), 400

    if not origin or not destination or origin == destination:
        return jsonify({
            "error": "Both from and to cities are required."
        }), 400

    if target_price <= 0:
        return jsonify({
            "error": "Please enter a target price greater than 0."
        }), 400

    alerts = load_alerts()

    alert = {
        "id": uuid.uuid4().hex,
        "email": email,
        "origin": origin,
        "destination": destination,
        "targetPrice": target_price,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "notified": False,
        "notifiedAt": None
    }

    alerts.append(alert)
    save_alerts(alerts)

    return jsonify({
        "status": "created",
        "message": (
            f"You'll be emailed at {email} when the {city_name(origin)} to "
            f"{city_name(destination)} fare drops to ₹{round(target_price):,} "
            "or below (checked once a day)."
        )
    }), 201


@app.get("/api/alerts")
def list_alerts():
    email = str(request.args.get("email") or "").strip()

    if not EMAIL_PATTERN.match(email):
        return jsonify({
            "error": "A valid email address is required."
        }), 400

    alerts = [
        alert
        for alert in load_alerts()
        if alert.get("email", "").lower() == email.lower()
    ]

    return jsonify({"alerts": alerts})


# --------------------------------------------------
# SERVER START
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False
    )
