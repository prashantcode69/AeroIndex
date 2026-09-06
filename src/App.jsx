import { useEffect, useState } from "react";

import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  BellRing,
  CalendarDays,
  CircleDollarSign,
  Clock3,
  Minus,
  Plane,
  Search,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const fallbackChartData = {
  Weekly: [
    { name: "Mon", avg: 8200, low: 6800 },
    { name: "Tue", avg: 7600, low: 6200 },
    { name: "Wed", avg: 8900, low: 7100 },
    { name: "Thu", avg: 7200, low: 5900 },
    { name: "Fri", avg: 9400, low: 7600 },
    { name: "Sat", avg: 8600, low: 6900 },
    { name: "Sun", avg: 7900, low: 6400 },
  ],

  Monthly: [
    { name: "Week 1", avg: 8200, low: 6800 },
    { name: "Week 2", avg: 7600, low: 6100 },
    { name: "Week 3", avg: 9100, low: 7300 },
    { name: "Week 4", avg: 7900, low: 6500 },
  ],

  Yearly: [
    { name: "Jan", avg: 7800, low: 6200 },
    { name: "Mar", avg: 8500, low: 6800 },
    { name: "May", avg: 9200, low: 7400 },
    { name: "Jul", avg: 10800, low: 8900 },
    { name: "Sep", avg: 8600, low: 6900 },
    { name: "Nov", avg: 8200, low: 6500 },
  ],
};

const API_BASE = "http://127.0.0.1:5000";

// Actively tracked routes with real collected data - shown as quick-select
// chips so a demo doesn't depend on typing city names correctly live.
const POPULAR_ROUTES = [
  { from: "Delhi", to: "Mumbai" },
  { from: "Delhi", to: "Goa" },
  { from: "Delhi", to: "Hyderabad" },
  { from: "Mumbai", to: "Bengaluru" },
  { from: "Delhi", to: "Chennai" },
  { from: "Delhi", to: "Kolkata" },
];

function matchesCityQuery(city, query) {
  const cleanQuery = query.trim().toLowerCase();

  if (!cleanQuery) {
    return false;
  }

  return (
    city.name.toLowerCase().includes(cleanQuery) ||
    city.code.toLowerCase().includes(cleanQuery)
  );
}

async function getAirfareData(from, to, onProgress) {
  const refreshResponse = await fetch(
    `${API_BASE}/api/refresh`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from,
        to,
      }),
    }
  );

  if (!refreshResponse.ok) {
    throw new Error("Pipeline start nahi ho paaya.");
  }

  const refreshData = await refreshResponse.json();

  // Route recently collect ho chuka hai toh scraping dobara
  // start nahi hoti - seedha cached data return hota hai.
  if (refreshData.status === "cached") {
    onProgress?.({ running: false, stage: "cached" });
  } else {
    // Pipeline complete hone tak status check karo - har poll par
    // asli progress (kitne booking windows scrape ho chuke hain)
    // report karte hain, fake spinner nahi.
    for (let attempt = 0; attempt < 240; attempt++) {
      const statusResponse = await fetch(
        `${API_BASE}/api/refresh-status`
      );

      const statusData = await statusResponse.json();

      onProgress?.(statusData);

      if (!statusData.running) {
        break;
      }

      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }

  onProgress?.({ running: false, stage: "finalizing" });

  const response = await fetch(
    `${API_BASE}/api/airfare?from=${encodeURIComponent(
      from
    )}&to=${encodeURIComponent(to)}`
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Unable to fetch airfare data");
  }

  return data;
}

function getProgressInfo(progress) {
  if (!progress) {
    return { percent: 8, message: "Starting live fare search..." };
  }

  if (progress.stage === "cached") {
    return { percent: 100, message: "Loading recently collected data..." };
  }

  if (progress.stage === "scraping") {
    const total = progress.totalWindows || 4;
    const done = progress.windowsCompleted || 0;

    return {
      percent: 10 + Math.round((done / total) * 55),
      message: `Searching live fares across ${total} booking windows (${done}/${total} done)...`,
    };
  }

  if (progress.stage === "analyzing") {
    return { percent: 75, message: "Comparing fares across airlines..." };
  }

  if (progress.stage === "computing") {
    return { percent: 88, message: "Calculating your Airfare Index..." };
  }

  if (progress.stage === "finalizing" || progress.stage === "done") {
    return { percent: 97, message: "Finalizing results..." };
  }

  if (progress.stage === "failed") {
    return { percent: 100, message: "Scrape hit an error - retrying fetch..." };
  }

  return { percent: 12, message: "Starting live fare search..." };
}

function formatCurrency(value) {
  const amount = Number(value);

  if (!Number.isFinite(amount)) {
    return "--";
  }

  return `₹${Math.round(amount).toLocaleString("en-IN")}`;
}

function formatAirlineData(airline, averageFare) {
  const fare = Number(
    airline.fare || airline.lowestFare || airline.averageFare || 0
  );

  const average = Number(averageFare || 0);

  const airlineCodes = {
    IndiGo: "6E",
    "Air India": "AI",
    "Air India Express": "IX",
    "Akasa Air": "QP",
    Vistara: "UK",
    SpiceJet: "SG",
  };

  const difference =
    average > 0 ? ((fare - average) / average) * 100 : null;

  return {
    name: airline.name || "Unknown Airline",

    code:
      airline.code ||
      airlineCodes[airline.name] ||
      String(airline.name || "NA")
        .slice(0, 2)
        .toUpperCase(),

    price: formatCurrency(fare),

    avg: formatCurrency(airline.averageFare || fare),

    diff:
      difference === null
        ? "--"
        : `${difference > 0 ? "+" : ""}${difference.toFixed(1)}%`,

    isCheaper: difference !== null && difference < 0,
  };
}

function createLiveChartData(history, averageFare, period) {
  if (Array.isArray(history) && history.length > 1) {
    return history.map((item) => ({
      name: item.name || item.date,
      avg: Number(item.avg || item.averageFare || 0),
      low: Number(item.low || item.lowestFare || 0),
    }));
  }

  const average = Number(averageFare || 0);

  if (!Number.isFinite(average) || average <= 0) {
    return fallbackChartData[period];
  }

  if (period === "Weekly") {
    return [
      {
        name: "Mon",
        avg: Math.round(average * 0.96),
        low: Math.round(average * 0.82),
      },
      {
        name: "Tue",
        avg: Math.round(average * 0.98),
        low: Math.round(average * 0.84),
      },
      {
        name: "Wed",
        avg: Math.round(average * 1.02),
        low: Math.round(average * 0.87),
      },
      {
        name: "Thu",
        avg: Math.round(average * 0.99),
        low: Math.round(average * 0.85),
      },
      {
        name: "Fri",
        avg: Math.round(average * 1.04),
        low: Math.round(average * 0.89),
      },
      {
        name: "Sat",
        avg: Math.round(average * 1.01),
        low: Math.round(average * 0.86),
      },
      {
        name: "Sun",
        avg: Math.round(average),
        low: Math.round(average * 0.84),
      },
    ];
  }

  if (period === "Monthly") {
    return [
      {
        name: "Week 1",
        avg: Math.round(average * 0.97),
        low: Math.round(average * 0.83),
      },
      {
        name: "Week 2",
        avg: Math.round(average * 0.99),
        low: Math.round(average * 0.85),
      },
      {
        name: "Week 3",
        avg: Math.round(average * 1.03),
        low: Math.round(average * 0.88),
      },
      {
        name: "Week 4",
        avg: Math.round(average),
        low: Math.round(average * 0.84),
      },
    ];
  }

  return [
    {
      name: "Jan",
      avg: Math.round(average * 0.94),
      low: Math.round(average * 0.81),
    },
    {
      name: "Mar",
      avg: Math.round(average * 0.98),
      low: Math.round(average * 0.84),
    },
    {
      name: "May",
      avg: Math.round(average * 1.02),
      low: Math.round(average * 0.87),
    },
    {
      name: "Jul",
      avg: Math.round(average * 1.06),
      low: Math.round(average * 0.9),
    },
    {
      name: "Sep",
      avg: Math.round(average * 1.01),
      low: Math.round(average * 0.86),
    },
    {
      name: "Nov",
      avg: Math.round(average),
      low: Math.round(average * 0.84),
    },
  ];
}

function App() {
  const [view, setView] = useState("hero");
  const [period, setPeriod] = useState("Monthly");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [error, setError] = useState("");
  const [routeData, setRouteData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(null);

  const [marketData, setMarketData] = useState(null);
  const [marketLoading, setMarketLoading] = useState(false);
  const [marketError, setMarketError] = useState("");

  const [alertEmail, setAlertEmail] = useState("");
  const [alertTargetPrice, setAlertTargetPrice] = useState("");
  const [alertMessage, setAlertMessage] = useState("");
  const [alertError, setAlertError] = useState("");
  const [alertSubmitting, setAlertSubmitting] = useState(false);

  const [cities, setCities] = useState([]);
  const [fromSuggestOpen, setFromSuggestOpen] = useState(false);
  const [toSuggestOpen, setToSuggestOpen] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/cities`)
      .then((response) => response.json())
      .then((data) => setCities(data.cities || []))
      .catch(() => setCities([]));
  }, []);

  const cleanFrom = from.trim();
  const cleanTo = to.trim();

  const fromSuggestions = cities
    .filter((city) => matchesCityQuery(city, cleanFrom))
    .slice(0, 6);

  const toSuggestions = cities
    .filter((city) => matchesCityQuery(city, cleanTo))
    .slice(0, 6);

  const loadRoute = async (fromValue, toValue) => {
    setError("");
    setLoading(true);
    setProgress(null);

    try {
      const data = await getAirfareData(
        fromValue.trim(),
        toValue.trim(),
        setProgress
      );

      setFrom(fromValue);
      setTo(toValue);
      setRouteData(data);
      setAlertMessage("");
      setAlertError("");
      setView("dashboard");
    } catch (err) {
      setError(
        err.message ||
          "Backend se data nahi aa raha. Check karo Flask server running hai ya nahi."
      );
    } finally {
      setLoading(false);
      setProgress(null);
    }
  };

  const handleGetIndex = () => {
    if (!cleanFrom || !cleanTo) {
      setError("Please enter both departure and arrival cities.");
      return;
    }

    if (cleanFrom.toLowerCase() === cleanTo.toLowerCase()) {
      setError("Departure and arrival cities cannot be the same.");
      return;
    }

    loadRoute(cleanFrom, cleanTo);
  };

  const handleEditRoute = () => {
    setView("hero");
    setError("");
  };

  const handleShowMarket = async () => {
    setView("market");
    setMarketError("");
    setMarketLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/market-overview`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Unable to load market overview");
      }

      setMarketData(data);
    } catch (err) {
      setMarketError(
        err.message ||
          "Backend se market overview nahi mila. Check karo Flask server running hai ya nahi."
      );
    } finally {
      setMarketLoading(false);
    }
  };

  const handleAlertSubmit = async (e) => {
    e.preventDefault();

    setAlertMessage("");
    setAlertError("");

    if (!alertEmail.trim() || !alertTargetPrice) {
      setAlertError("Please enter both an email and a target price.");
      return;
    }

    setAlertSubmitting(true);

    try {
      const response = await fetch(`${API_BASE}/api/alerts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: alertEmail.trim(),
          from: routeData?.fromCode || cleanFrom,
          to: routeData?.toCode || cleanTo,
          targetPrice: Number(alertTargetPrice),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Unable to create alert");
      }

      setAlertMessage(data.message || "Alert created.");
      setAlertTargetPrice("");
    } catch (err) {
      setAlertError(err.message || "Alert create nahi ho paaya.");
    } finally {
      setAlertSubmitting(false);
    }
  };

  const progressInfo = getProgressInfo(progress);

  const averageFare = Number(routeData?.averageFare || 0);
  const indexValue = Number(routeData?.index || 0);

  const dashboardAirlines = (routeData?.airlines || [])
    .map((airline) => formatAirlineData(airline, averageFare))
    .sort((a, b) => {
      const priceA = Number(a.price.replace(/[₹,]/g, "") || 0);
      const priceB = Number(b.price.replace(/[₹,]/g, "") || 0);

      return priceA - priceB;
    });

  const progressWidth = Math.min(
    Math.max(((indexValue - 100) / 50) * 100, 0),
    100
  );

  const liveChartData = createLiveChartData(
    routeData?.history || [],
    averageFare,
    period
  );

  const bookingUrl =
    routeData?.bookingUrl || "https://www.google.com/travel/flights";

  return (
    <main className="app">
      <div className="background-glow glow-one" />
      <div className="background-glow glow-two" />

      <nav className="navbar">
        <div className="brand">
          <div className="brand-mark">
            <Plane size={21} strokeWidth={2.5} />
          </div>

          <span>
            Aero<span>Index</span>
          </span>
        </div>

        <div className="nav-links">
          <a
            href="#market"
            onClick={(e) => {
              e.preventDefault();
              handleShowMarket();
            }}
          >
            Market overview
          </a>
          <a className="nav-secondary-link" href="#how-it-works">
            How it works
          </a>

          <button
            className="nav-login"
            onClick={() => setView("hero")}
          >
            Explore index
            <ArrowUpRight size={16} />
          </button>
        </div>
      </nav>

      {view === "hero" ? (
        <section className="hero-section">
          <div className="hero-copy">
            <div className="eyebrow">
              <Sparkles size={15} />
              <span>SMART AIRFARE INTELLIGENCE</span>
            </div>

            <h1>
              Know the price.
              <br />
              <span>Choose the flight.</span>
            </h1>

            <p className="hero-description">
              Compare airfare across airlines, understand price differences,
              and find the right time to fly.
            </p>

            <div className="search-card">
              <div className="search-field">
                <div className="field-icon">
                  <Plane size={18} />
                </div>

                <div className="city-autocomplete">
                  <label>FROM</label>

                  <input
                    value={from}
                    onChange={(e) => {
                      setFrom(e.target.value);
                      setError("");
                      setFromSuggestOpen(true);
                    }}
                    onFocus={() => setFromSuggestOpen(true)}
                    onBlur={() =>
                      setTimeout(() => setFromSuggestOpen(false), 120)
                    }
                    placeholder="e.g. Delhi"
                    autoComplete="off"
                  />

                  {fromSuggestOpen && fromSuggestions.length > 0 && (
                    <div className="city-suggestions">
                      {fromSuggestions.map((city) => (
                        <div
                          key={city.code}
                          className="city-suggestion-item"
                          onMouseDown={() => {
                            setFrom(city.name);
                            setFromSuggestOpen(false);
                          }}
                        >
                          <strong>{city.name}</strong>
                          <span>{city.code}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="route-divider">
                <ArrowRight size={18} />
              </div>

              <div className="search-field">
                <div className="field-icon">
                  <Plane size={18} />
                </div>

                <div className="city-autocomplete">
                  <label>TO</label>

                  <input
                    value={to}
                    onChange={(e) => {
                      setTo(e.target.value);
                      setError("");
                      setToSuggestOpen(true);
                    }}
                    onFocus={() => setToSuggestOpen(true)}
                    onBlur={() =>
                      setTimeout(() => setToSuggestOpen(false), 120)
                    }
                    placeholder="e.g. Mumbai"
                    autoComplete="off"
                  />

                  {toSuggestOpen && toSuggestions.length > 0 && (
                    <div className="city-suggestions">
                      {toSuggestions.map((city) => (
                        <div
                          key={city.code}
                          className="city-suggestion-item"
                          onMouseDown={() => {
                            setTo(city.name);
                            setToSuggestOpen(false);
                          }}
                        >
                          <strong>{city.name}</strong>
                          <span>{city.code}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <button
                className="get-index-btn"
                onClick={handleGetIndex}
                disabled={loading}
              >
                {loading ? "Searching..." : "Get Index"}
                <ArrowRight size={18} />
              </button>
            </div>

            {loading && (
              <div className="search-progress">
                <div className="search-progress-bar">
                  <div style={{ width: `${progressInfo.percent}%` }} />
                </div>

                <span>{progressInfo.message}</span>
              </div>
            )}

            {!loading && error && (
              <p
                style={{
                  marginTop: "12px",
                  color: "#c2410c",
                  fontSize: "13px",
                }}
              >
                {error}
              </p>
            )}

            <div className="hero-trust">
              <div className="trust-item">
                <CircleDollarSign size={17} />
                <span>Compare smarter</span>
              </div>

              <div className="trust-item">
                <BarChart3 size={17} />
                <span>Track price trends</span>
              </div>
            </div>

            <div className="popular-routes">
              <span>Popular routes</span>

              <div className="popular-routes-list">
                {POPULAR_ROUTES.map((route) => (
                  <button
                    key={`${route.from}-${route.to}`}
                    className="popular-route-chip"
                    onClick={() => loadRoute(route.from, route.to)}
                    disabled={loading}
                  >
                    {route.from} → {route.to}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="hero-visual">
            <div className="route-visual">
              <div className="route-topline">
                <span>LIVE ROUTE ANALYSIS</span>

                <span className="route-status">
                  <i /> Updated now
                </span>
              </div>

              <div className="route-map">
                <div className="map-grid" />

                <div className="map-line line-one" />
                <div className="map-line line-two" />
                <div className="map-line line-three" />

                <div className="airport airport-delhi">
                  <span className="airport-dot" />

                  <div>
                    <strong>
                      {cleanFrom
                        ? cleanFrom.slice(0, 3).toUpperCase()
                        : "DEL"}
                    </strong>

                    <small>{cleanFrom || "Delhi"}</small>
                  </div>
                </div>

                <div className="airport airport-mumbai">
                  <span className="airport-dot" />

                  <div>
                    <strong>
                      {cleanTo
                        ? cleanTo.slice(0, 3).toUpperCase()
                        : "BOM"}
                    </strong>

                    <small>{cleanTo || "Mumbai"}</small>
                  </div>
                </div>

                <div className="route-plane">
                  <Plane size={20} />
                </div>

                <div className="route-distance">
                  <span>Direct route</span>

                  <strong>
                    {routeData?.distance || "1,148 km"}
                  </strong>
                </div>
              </div>

              <div className="route-bottom">
                <div>
                  <span>Current index</span>
                  <strong>{routeData?.index ?? "--"}</strong>
                </div>

                <div>
                  <span>Average fare</span>

                  <strong>
                    {routeData
                      ? formatCurrency(routeData.averageFare)
                      : "--"}
                  </strong>
                </div>

                <div className="route-change">
                  <TrendingDown size={15} />

                  <span>
                    {routeData?.priceChange || "Live data"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>
      ) : view === "dashboard" ? (
        <section className="dashboard-section" id="dashboard">
          <div className="dashboard-heading">
            <div>
              <div className="breadcrumb">
                AeroIndex <span>/</span> Route analysis
              </div>

              <h2>
                {cleanFrom}
                <ArrowRight size={24} />
                {cleanTo}
              </h2>

              <p>Live airfare comparison across available airlines</p>
            </div>

            <button
              className="edit-route-btn"
              onClick={handleEditRoute}
            >
              <Search size={16} />
              Edit route
            </button>
          </div>

          <div className="stats-grid">
            <div className="stat-card index-card">
              <div className="stat-top">
                <span>Airfare Index</span>

                <div className="status-pill">
                  <span />

                  {indexValue > 100
                    ? "Above cheapest fare"
                    : "At cheapest fare"}
                </div>
              </div>

              <div className="index-score">
                {routeData?.index ?? "--"}
              </div>

              <div className="index-progress">
                <div style={{ width: `${progressWidth}%` }} />
              </div>

              <div className="stat-bottom">
                <span>Based on current market prices</span>
                <TrendingDown size={17} />
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-label">
                <CircleDollarSign size={17} />
                Average fare
              </div>

              <div className="stat-value">
                {routeData
                  ? formatCurrency(routeData.averageFare)
                  : "--"}
              </div>

              <div className="stat-change positive">
                <TrendingDown size={15} />
                {routeData?.priceChange || "Live data"}
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-label">
                <Clock3 size={17} />
                Best time to book
              </div>

              <div className="stat-value">
                {routeData?.bestBookingWindow || "--"}
              </div>

              <div className="stat-change neutral">
                <CalendarDays size={15} />
                Before departure
              </div>
            </div>
          </div>

          <div className="dashboard-grid">
            <div className="panel chart-panel">
              <div className="panel-heading">
                <div>
                  <span className="panel-kicker">PRICE MOVEMENT</span>
                  <h3>How fares are moving</h3>
                </div>

                <div className="period-tabs">
                  {["Weekly", "Monthly", "Yearly"].map((item) => (
                    <button
                      key={item}
                      className={period === item ? "active" : ""}
                      onClick={() => setPeriod(item)}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>

              <div className="chart-legend">
                <span>
                  <i className="legend-dot average" />
                  Average fare
                </span>

                <span>
                  <i className="legend-dot lowest" />
                  Lowest fare
                </span>
              </div>

              <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={liveChartData}
                    margin={{
                      top: 20,
                      right: 10,
                      left: 0,
                      bottom: 0,
                    }}
                  >
                    <defs>
                      <linearGradient
                        id="avgGradient"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="0%"
                          stopColor="#3155a5"
                          stopOpacity={0.18}
                        />

                        <stop
                          offset="100%"
                          stopColor="#3155a5"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>

                    <CartesianGrid
                      strokeDasharray="4 4"
                      stroke="#e5e9f0"
                      vertical={false}
                    />

                    <XAxis
                      dataKey="name"
                      axisLine={false}
                      tickLine={false}
                      tick={{
                        fill: "#8c96a7",
                        fontSize: 12,
                      }}
                    />

                    <YAxis
                      axisLine={false}
                      tickLine={false}
                      tick={{
                        fill: "#8c96a7",
                        fontSize: 12,
                      }}
                      tickFormatter={(value) =>
                        `₹${Math.round(value / 1000)}k`
                      }
                    />

                    <Tooltip
                      contentStyle={{
                        background: "#172235",
                        border: "1px solid #30425b",
                        borderRadius: "12px",
                        color: "#fff",
                      }}
                      formatter={(value, name) => [
                        formatCurrency(value),
                        name === "avg"
                          ? "Average fare"
                          : "Lowest fare",
                      ]}
                    />

                    <Area
                      type="monotone"
                      dataKey="avg"
                      stroke="#3155a5"
                      strokeWidth={3}
                      fill="url(#avgGradient)"
                    />

                    <Area
                      type="monotone"
                      dataKey="low"
                      stroke="#b9c2d0"
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      fill="none"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="panel insight-panel">
              <div className="panel-kicker">SMART INSIGHT</div>

              <div className="insight-icon">
                {routeData?.trend?.direction === "rising" ? (
                  <TrendingUp size={22} />
                ) : routeData?.trend?.direction === "falling" ? (
                  <TrendingDown size={22} />
                ) : routeData?.trend?.direction === "stable" ? (
                  <Minus size={22} />
                ) : (
                  <Sparkles size={22} />
                )}
              </div>

              <h3>Live airfare analysis</h3>

              <p>
                Current average fare is{" "}
                <strong>
                  {routeData
                    ? formatCurrency(routeData.averageFare)
                    : "--"}
                </strong>
                .{" "}
                {routeData?.trend?.recommendation ||
                  "This index is calculated from the latest collected Google Flights fare records."}
              </p>

              <div className="insight-route">
                <div className="insight-route-line" />

                <span>{cleanFrom}</span>
                <ArrowRight size={15} />
                <span>{cleanTo}</span>
              </div>

              <button
                className="insight-btn"
                onClick={() => window.open(bookingUrl, "_blank")}
              >
                View booking options
                <ArrowUpRight size={16} />
              </button>
            </div>
          </div>

          <div className="panel airlines-panel">
            <div className="panel-heading">
              <div>
                <span className="panel-kicker">
                  AIRLINE COMPARISON
                </span>

                <h3>Find the best fare</h3>
              </div>

              <button
                className="view-all-btn"
                onClick={() =>
                  alert("All available airlines are already shown below.")
                }
              >
                View all
                <ArrowRight size={15} />
              </button>
            </div>

            <div className="airline-list">
              {dashboardAirlines.length > 0 ? (
                dashboardAirlines.map((airline, index) => (
                  <div
                    className="airline-row"
                    key={`${airline.name}-${index}`}
                  >
                    <div className="airline-name">
                      <div className="airline-logo">
                        {airline.code}
                      </div>

                      <div>
                        <strong>{airline.name}</strong>

                        {index === 0 && (
                          <span className="best-badge">
                            BEST VALUE
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="airline-metric">
                      <span>Lowest fare</span>
                      <strong>{airline.price}</strong>
                    </div>

                    <div className="airline-metric">
                      <span>Average fare</span>
                      <strong>{airline.avg}</strong>
                    </div>

                    <div className="airline-metric difference">
                      <span>Difference</span>

                      <strong
                        style={{
                          color: airline.isCheaper
                            ? "#16a34a"
                            : "#3155a5",
                        }}
                      >
                        {airline.diff}
                      </strong>
                    </div>

                    <button
                      className="airline-arrow"
                      onClick={() => window.open(bookingUrl, "_blank")}
                    >
                      <ArrowUpRight size={17} />
                    </button>
                  </div>
                ))
              ) : (
                <div
                  style={{
                    padding: "28px 0",
                    textAlign: "center",
                    color: "#8c96a7",
                  }}
                >
                  No airline data available for this route yet.
                </div>
              )}
            </div>
          </div>

          <div className="panel alert-panel">
            <div className="panel-heading">
              <div>
                <span className="panel-kicker">PRICE ALERT</span>
                <h3>Get notified if this fare drops</h3>
              </div>
            </div>

            <form className="alert-form" onSubmit={handleAlertSubmit}>
              <div className="alert-field">
                <label>EMAIL</label>
                <input
                  type="email"
                  value={alertEmail}
                  onChange={(e) => setAlertEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </div>

              <div className="alert-field">
                <label>TARGET PRICE (₹)</label>
                <input
                  type="number"
                  min="1"
                  value={alertTargetPrice}
                  onChange={(e) => setAlertTargetPrice(e.target.value)}
                  placeholder={
                    routeData?.lowestFare
                      ? String(Math.round(routeData.lowestFare * 0.95))
                      : "e.g. 6000"
                  }
                />
              </div>

              <button
                className="alert-submit-btn"
                type="submit"
                disabled={alertSubmitting}
              >
                <BellRing size={16} />
                {alertSubmitting ? "Saving..." : "Alert me"}
              </button>
            </form>

            {alertMessage && (
              <p className="alert-feedback success">{alertMessage}</p>
            )}

            {alertError && (
              <p className="alert-feedback error">{alertError}</p>
            )}
          </div>
        </section>
      ) : (
        <section className="dashboard-section" id="market">
          <div className="dashboard-heading">
            <div>
              <div className="breadcrumb">
                AeroIndex <span>/</span> Market overview
              </div>

              <h2>National Airfare Index</h2>

              <p>
                How every tracked route is currently pricing relative to
                its own cheapest fare - higher means more inflated right
                now, lower means closer to its floor.
              </p>
            </div>

            <button className="edit-route-btn" onClick={() => setView("hero")}>
              <Search size={16} />
              Analyse a route
            </button>
          </div>

          {loading && (
            <div className="search-progress market-progress">
              <div className="search-progress-bar">
                <div style={{ width: `${progressInfo.percent}%` }} />
              </div>

              <span>{progressInfo.message}</span>
            </div>
          )}

          {marketLoading && (
            <p style={{ color: "#8c96a7", fontSize: "13px" }}>
              Loading market overview...
            </p>
          )}

          {marketError && (
            <p style={{ color: "#c2410c", fontSize: "13px" }}>
              {marketError}
            </p>
          )}

          {!marketLoading && !marketError && marketData && (
            <>
              <div className="panel market-summary-panel">
                <div className="stat-label">
                  <BarChart3 size={17} />
                  Market average index
                </div>

                <div className="stat-value">
                  {marketData.marketAverageIndex ?? "--"}
                </div>

                <div className="stat-change neutral">
                  Across {marketData.routeCount} tracked route
                  {marketData.routeCount === 1 ? "" : "s"}
                </div>
              </div>

              <div className="panel airlines-panel">
                <div className="panel-heading">
                  <div>
                    <span className="panel-kicker">ALL ROUTES</span>
                    <h3>Sorted from most to least inflated</h3>
                  </div>
                </div>

                <div className="airline-list">
                  {marketData.routes.length > 0 ? (
                    marketData.routes.map((route, index) => (
                      <div
                        className="airline-row market-row"
                        key={`${route.fromCode}-${route.toCode}-${index}`}
                        onClick={() => loadRoute(route.from, route.to)}
                      >
                        <div className="airline-name">
                          <div className="airline-logo">
                            {route.fromCode}
                          </div>

                          <div>
                            <strong>
                              {route.from} → {route.to}
                            </strong>

                            {route.trend?.direction === "rising" && (
                              <span
                                className="best-badge"
                                style={{ color: "#c2410c" }}
                              >
                                TRENDING UP
                              </span>
                            )}

                            {route.trend?.direction === "falling" && (
                              <span className="best-badge">
                                TRENDING DOWN
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="airline-metric">
                          <span>Index</span>
                          <strong>{route.index}</strong>
                        </div>

                        <div className="airline-metric">
                          <span>Average fare</span>
                          <strong>{formatCurrency(route.averageFare)}</strong>
                        </div>

                        <div className="airline-metric difference">
                          <span>Best time to book</span>
                          <strong>{route.bestBookingWindow}</strong>
                        </div>

                        <button className="airline-arrow">
                          <ArrowUpRight size={17} />
                        </button>
                      </div>
                    ))
                  ) : (
                    <div
                      style={{
                        padding: "28px 0",
                        textAlign: "center",
                        color: "#8c96a7",
                      }}
                    >
                      No routes tracked yet - analyse a route to add it
                      here.
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </section>
      )}

      <footer className="footer">
        <div className="brand">
          <div className="brand-mark">
            <Plane size={17} />
          </div>

          <span>
            Aero<span>Index</span>
          </span>
        </div>

        <span>Airfare intelligence, simplified.</span>

        <span style={{ maxWidth: "320px", textAlign: "right" }}>
          Fare data is sourced from publicly available Google Flights
          search results for demonstration purposes.
        </span>
      </footer>
    </main>
  );
}

export default App;
