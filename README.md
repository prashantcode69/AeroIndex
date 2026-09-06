# AeroIndex

Full-stack airfare intelligence platform. Instead of just listing flights, AeroIndex converts collected fare data into an **Airfare Index**, airline-by-airline comparison, a data-driven **best time to book** signal, a **trend-based book-now-vs-wait recommendation**, a national **Market Overview** across all tracked routes, and **price-drop email alerts** — for any Indian route a user searches, not just a fixed list.

## Stack

- **Frontend:** React 19 + Vite, Recharts for charts, Lucide for icons.
- **Backend:** Python Flask REST API (`Backend/app.py`).
- **Data collection:** Playwright scrapes Google Flights search results across multiple booking windows (7 / 15 / 30 / 45 days before departure) for a given route.
- **Storage:** Flat JSON files, one folder per route (`Backend/data/routes/{ORIGIN}_{DEST}/`), plus per-route daily history snapshots.

## Running it

**Backend**
```
cd Backend
pip install -r requirements.txt
python -m playwright install chromium
python app.py
```

**Frontend**
```
npm install
npm run dev
```

## Any route, not just a fixed list

Typing a city that isn't in the curated 55-city autocomplete list (`GET /api/cities`) still works — `/api/refresh` will scrape that route live on first request. This was verified end-to-end for never-before-scraped routes. The only real limitation is Google Flights itself: some low-traffic connecting routes show "Price unavailable" in the summary view, in which case AeroIndex honestly reports no fare data rather than fabricating a number.

A never-before-scraped route scrapes 4 booking windows (7/15/30/45 days out) **in parallel** (`run_pipeline.py` uses a thread pool, one headless browser per window) — roughly 20-25 seconds total instead of 60-90+ seconds sequential. Already-cached routes (<24h old) still return instantly.

## Keeping data fresh for a demo

`/api/refresh` caches for 24h so a live demo never depends on a scrape succeeding at that exact moment. To pre-seed/refresh the 8 tracked demo routes (DEL↔BOM/GOI/HYD/AMD/CCU/MAA, BOM↔BLR, BLR↔HYD) in one go:
```
cd Backend
python daily_refresh.py
```
To run this automatically every day (recommended before a demo, so trend charts show real multi-day movement), register a Windows Scheduled Task:
```
schtasks /create /tn "AeroIndex Daily Refresh" /tr "<path-to-python.exe> <path-to-Backend>\daily_refresh.py" /sc daily /st 09:00 /f
```

## Price alerts (optional email setup)

Alert matching always works (`POST /api/alerts`, checked every refresh via `pipeline/alert_checker.py`). To make it actually send email instead of just logging "would have emailed X": copy `Backend/.env.example` to `Backend/.env` and fill in real SMTP credentials (a Gmail App Password works well). `.env` is gitignored — never commit real credentials.

## API

- `GET /api/cities` — the curated city list (code + display name) used for search autocomplete.
- `POST /api/refresh` — triggers a fresh scrape for a route (`{"from": "...", "to": "..."}`). Returns cached data immediately if refreshed within 24h (pass `"force": true` to bypass).
- `GET /api/refresh-status` — whether a scrape is currently running.
- `GET /api/airfare?from=...&to=...` — index, fare stats, airline comparison, best-booking-window breakdown, price history, and trend recommendation for a route.
- `GET /api/market-overview` — every tracked route ranked by index, plus a national market average index.
- `POST /api/alerts` (`{email, from, to, targetPrice}`) and `GET /api/alerts?email=...` — price-drop alerts.

## Data source & methodology

Fare data is collected from **publicly available Google Flights search results** for prototype/demonstration purposes. It is not sourced from a licensed fare API and should not be treated as booking-grade pricing. A production version of AeroIndex would integrate a licensed airfare data provider (e.g. Amadeus, Skyscanner) instead of scraping.

- **Airfare Index** = current average fare ÷ current lowest fare × 100, computed for the route's reference booking window (15 days out).
- **Best time to book** is computed by comparing the average fare AeroIndex actually collected across four booking windows (7/15/30/45 days before departure) for the route and picking the cheapest — not a hardcoded estimate.
- **Trend recommendation** compares the last two days of a route's saved history to suggest booking now vs. waiting — needs 2+ days of collected history to activate.
- **Airline comparison** groups the same reference-window records by airline to compare lowest/average fares.

## Project status

This is a hackathon-stage prototype (built for SIH). See the codebase for what's implemented vs. planned — future scope includes ML-based fare prediction, user accounts, and cloud deployment.
