# System Implementation — Comprehensive Technical Record
### AI-Powered Smart Microgrid Analytics Web Application
*For reference in Chapters 1–5 of the thesis*
*Last updated: 2026-05-07*

---

## Chapter 1 — Introduction

### 1.1 Problem Statement
Nigeria and other developing nations face persistent electricity supply challenges: intermittent grid supply, over-reliance on diesel generators, and no visibility into consumption patterns or renewable energy potential. Existing commercial solutions (SolarEdge, Enphase) are cloud-locked, cost-prohibitive, and unavailable offline.

This project develops an open, AI-driven microgrid analytics platform that:
- Forecasts solar and wind availability 48 hours ahead using three ML models
- Optimises battery charge/dispatch using Linear Programming
- Detects anomalies in energy variables using a three-method ensemble
- Supports multiple countries, building types, and tariff structures

### 1.2 Research Objectives
1. Design and implement an ERA5-trained ML pipeline for renewable energy forecasting
2. Implement LP-based battery optimisation with time-of-use pricing
3. Develop an ensemble anomaly detection system
4. Build a full-stack web application accessible via browser on any device
5. Support real-world heterogeneity: multiple countries, building types, appliance loads, tariff bands

### 1.3 Technologies Used

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Data source | ERA5 reanalysis (Copernicus CDS) | Globally consistent, 0.25°×0.25° resolution, 1h temporal, freely available |
| ML framework | scikit-learn (RF, GB), XGBoost | Industry-standard, reproducible, no GPU requirement |
| Optimisation | PuLP (Linear Programming) | Exact LP solver, MILP-capable, open-source |
| Backend API | Flask (Python 3.11) | Lightweight, easy deployment, rich scientific library ecosystem |
| Frontend | React + Vite | Fast HMR, component-based UI, widely used |
| Database | MongoDB Atlas | Schema-flexible for user profiles, serverless-friendly |
| Hosting (backend) | Render.com | Free-tier web service; Flask/gunicorn deploy |
| Hosting (frontend) | Vercel | Zero-config Vite deploy, global CDN |
| Map | Mapbox GL JS | Globe projection, flyTo animation, satellite layer |
| Authentication | JWT + Google OAuth + Microsoft MSAL + Apple Sign In | Multi-provider; JWT for email/password |

### 1.4 Countries Supported
| Country   | Capital  | Coordinates     | Timezone         |
|-----------|----------|-----------------|------------------|
| Nigeria   | Abuja    | 9.08°N, 7.40°E  | Africa/Lagos     |
| Australia | Canberra | 35.28°S, 149.13°E | Australia/Sydney |
| Germany   | Berlin   | 52.52°N, 13.41°E | Europe/Berlin    |
| Canada    | Ottawa   | 45.42°N, 75.70°W | America/Toronto  |

---

## Chapter 2 — Literature Review

### 2.1 ERA5 Reanalysis Data
ERA5 (ECMWF Reanalysis v5) provides hourly estimates of atmospheric variables back to 1940 at 0.25° spatial resolution. Used in this project: solar radiation (ssrd), wind components (u10/v10), temperature (t2m), pressure (sp), precipitation (tp), dewpoint (d2m), cloud cover (tcc).

### 2.2 Machine Learning for Energy Forecasting
Three supervised regression models are compared (as specified in thesis Ch. 3.6.1):
- **Random Forest** — ensemble of decision trees; robust to noise; parallel inference
- **Gradient Boosting (sklearn)** — sequential boosting; captures complex feature interactions
- **XGBoost** — regularised gradient boosting; faster training; built-in feature importance

All three are trained on the same feature set and evaluated on a held-out 20% chronological test set. MAPE is not used as the primary metric because solar radiation is zero at night (undefined division); MAE and R² are used instead.

### 2.3 Linear Programming for Battery Dispatch
The battery optimisation problem is formulated as a constrained LP:
- **Objective:** minimise grid import cost over 24 hours
- **Decision variables:** hourly charge/discharge amounts
- **Constraints:** battery SoC bounds (10%–95%), max charge rate (C/4), energy conservation
- **Tariff:** time-of-use weighting — 1.5× peak (18:00–21:00), 0.8× off-peak (23:00–06:00)

### 2.4 Anomaly Detection
Three-method ensemble (majority vote, ≥2 of 3 must agree):
- Isolation Forest (tree-based isolation of outliers)
- Z-score (statistical deviation from mean)
- IQR (interquartile range fence: Q1 − 1.5×IQR, Q3 + 1.5×IQR)

---

## Chapter 3 — System Design

### 3.1 Data Pipeline

```
ERA5 NetCDF4 files (2008–2016)
        ↓  spatial average (xarray)
Hourly time-series CSV per country
        ↓  feature engineering
42-column feature matrix
        ↓  year-analog resampling (2017–2021 gap fill)
        ↓  merge with 2022–2024 processed data
        ↓  fix_lag_features.py (recompute lags on full series)
Final dataset: ~148,896 rows × 42 columns per country
```

**Feature engineering columns:**
| Column | Derivation |
|--------|-----------|
| `solar_radiation_wm2` | `ssrd / 3600` (J/m² → W/m²), clipped ≥ 0 |
| `temperature_celsius` | `t2m − 273.15` |
| `pressure` | `sp / 100` (Pa → hPa) |
| `wind_speed` | `√(u10² + v10²)` |
| `wind_direction` | `atan2(u10, v10) × 180/π mod 360` |
| `relative_humidity` | Magnus formula |
| `hour_sin/cos` | `sin/cos(2π·hour/24)` — cyclical encoding |
| `month_sin/cos` | `sin/cos(2π·month/12)` |
| `solar_lag_1h/24h/168h` | `shift(1/24/168)` |
| `wind_lag_1h/24h/168h` | `shift(1/24/168)` |
| Rolling 24h mean/std | `rolling(24).mean/std().shift(1)` |

**2017–2021 gap filling (year-analog resampling):**
Year D drawn randomly from 2008–2016, timestamps relabelled, Gaussian noise added (σ = 1% of std dev). Seeds: 2017←2009, 2018←2008, 2019←2012, 2020←2011, 2021←2011.

### 3.2 Backend Architecture

Flask REST API (`backend/app.py`) — 11 route blueprints:

| Blueprint | Prefix | Key Routes |
|-----------|--------|-----------|
| `auth_bp` | `/api/auth` | POST `/google`, `/microsoft`, `/apple`, `/login`, `/signup` |
| `forecast_bp` | `/api/forecast` | GET `/?country=nigeria&hours=48` |
| `optimize_bp` | `/api/optimize` | GET `/?country=nigeria&battery_kwh=15&panel_kw=8` |
| `anomaly_bp` | `/api/anomaly` | GET `/?country=nigeria&hours=48` |
| `user_bp` | `/api/user` | GET/PATCH `/profile` |
| `location_bp` | `/api/location` | GET `/?lat=X&lon=Y` |
| `weather_bp` | `/api/weather` | GET `/?country=nigeria` |

**Forecast response (three models side-by-side):**
```json
{
  "models_available": ["rf", "gb", "xgb"],
  "using_synthetic": false,
  "forecast": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "solar_rf": 320.1, "solar_gb": 318.5, "solar_xgb": 321.2,
      "wind_rf": 4.2,    "wind_gb": 4.1,    "wind_xgb": 4.3,
      "demand": 52.1
    }
  ]
}
```

**Physics-based fallback (when ML models not deployed):**
When `.pkl` files are absent, `forecast_routes.py` generates synthetic forecasts using:
- Solar: Gaussian curve `G(t) = G_peak × exp(−(t−noon)²/(2σ²))` with stochastic cloud factor
- Wind: Weibull distribution with diurnal amplitude variation
- All three model outputs use the same synthetic values; response includes `"using_synthetic": true`

**Optimisation (LP via PuLP):**
```
Minimise: Σ grid_import[t] × tariff[t]
Subject to:
  soc[t] = soc[t-1] + charge[t] × η − discharge[t]
  0.10 × battery_kwh ≤ soc[t] ≤ 0.95 × battery_kwh
  0 ≤ charge[t] ≤ battery_kwh / 4
  charge[t] + discharge[t] ≤ solar[t] + grid_import[t]
  tariff[t] = 1.5 if 18 ≤ t ≤ 21 else 0.8 if 23 ≤ t or t ≤ 6 else 1.0
```

**Anomaly detection ensemble:**
Each of the three methods (Isolation Forest, Z-score, IQR) votes independently on each hourly data point. A point is flagged as anomalous if ≥ 2 methods agree. Severity is normalised deviation from the cluster centre.

### 3.3 Database
**MongoDB Atlas** — primary data store for user profiles.
Key schema fields:
```
user_id, email, name, auth_provider, provider_id,
country, state, building_type, address,
peak_demand_kw, daily_kwh, appliances (array),
nigeria_band, electricity_rate,
created_at, last_login
```
Note: PostgreSQL was initially included but all production queries were migrated to MongoDB. The `database/postgres_handler.py` file exists but is not called in production.

### 3.4 Authentication
Four sign-in methods:
| Method | Flow | Token |
|--------|------|-------|
| Email/password | `POST /api/auth/signup` + `POST /api/auth/login` | JWT (HS256) |
| Google | `@react-oauth/google` button → `POST /api/auth/google` (verify id_token) | JWT |
| Microsoft | MSAL PKCE popup → `POST /api/auth/microsoft` (decode id_token) | JWT |
| Apple | `react-apple-login` popup → `POST /api/auth/apple` (decode id_token) | JWT |

Session management: 30-minute idle timeout in `AuthContext.jsx` (mouse/keyboard events reset timer).

### 3.5 Frontend Architecture

React + Vite (`microgrid-ui/`) — 8 pages, 12+ components.

**Pages:**
| Route | Component | Purpose |
|-------|-----------|---------|
| `/login` | `Login.jsx` | Multi-provider auth |
| `/onboarding` | `Onboarding.jsx` | 4-step setup wizard |
| `/` | `Dashboard.jsx` | Overview: map, weather, charts, anomalies |
| `/forecast` | `ForecastPage.jsx` | Full 48-hour forecast with model comparison |
| `/optimize` | `OptimizePage.jsx` | Battery dispatch schedule + LP strategy |
| `/anomaly` | `AnomalyPage.jsx` | Anomaly event list with severity badges |
| `/report` | `ReportPage.jsx` | Printable A4 report |
| `/settings` | `Settings.jsx` | Profile, language, theme, appliances |

**Key components:**
- `ForecastChart.jsx` — three model lines (RF emerald, GB amber, XGBoost rose) using Recharts
- `OptimizationChart.jsx` — ComposedChart: bar (battery SoC) + line (solar, demand, grid)
- `AnomalyPanel.jsx` — horizontal event cards with severity colour coding
- `WeatherWidget.jsx` — live weather from OpenWeatherMap
- `MapPanel.jsx` — Mapbox GL globe with flyTo animation and capital pin
- `ApplianceCalculator.jsx` — appliance load estimator with per-unit qty, hours, brand
- `Sidebar.jsx` — navigation, country selector, language pills, model legend

### 3.6 Appliance Load Estimation

The appliance calculator allows users to model their specific building's load profile instead of relying on generic defaults.

**Catalog structure:** Five building types × 3–10 appliances each. Each appliance has:
- `watts` — per-unit rated power (W)
- `hours` — default daily usage hours (editable by user)
- `icon`, `label`, `id`

**User inputs per appliance:**
1. Quantity (direct number input or +/− steppers)
2. Hours per day (editable, 0–24, replaces fixed defaults)
3. Brand name (optional free text, stored and shown in report)

**Calculation:**
```
peak_kw   = Σ (watts_i × qty_i) / 1000
daily_kwh = Σ (watts_i × qty_i × hours_i) / 1000
monthly_kwh = daily_kwh × 30
monthly_cost = monthly_kwh × rate[country][band]
```

**Nigeria NERC 2024 Tariff Bands:**
| Band | Supply (h/day) | Rate (₦/kWh) | Typical customer |
|------|---------------|-------------|-----------------|
| A    | 20+           | ₦225        | Central business districts |
| B    | 16–20         | ₦63         | Urban residential |
| C    | 12–16         | ₦50         | Peri-urban |
| D    | 8–12          | ₦43         | Semi-rural |
| E    | <8            | ₦40         | Rural |

**Impact on optimisation:** When `peak_demand_kw` and `daily_kwh` are set from the appliance calculator, the battery sizing on the Optimize page uses:
```
battery_kwh = max(5, ceil(daily_kwh × 0.5))
panel_kw    = max(2, ceil(peak_demand_kw × 1.2))
```
Instead of generic building-type defaults.

---

## Chapter 4 — Implementation

### 4.1 Data Collection and Processing Scripts

| Script | Purpose | Location |
|--------|---------|---------|
| `generate_2017_2024.py` | Full ERA5 pipeline: NetCDF → features → analog → merge | `c:/Users/.../Final Year Project/` |
| `fix_lag_features.py` | Recompute lags on full series; fill NaN | same |
| `retrain_models.py` | Train RF + GB + XGBoost; save `.pkl` and scalers | root of repo |

### 4.2 Deployment

**Backend — Render:**
```
Service type:    Web Service
Root directory:  backend/
Build command:   pip install -r requirements.txt
Start command:   gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT
Python version:  3.11.9  (pinned via backend/runtime.txt)
URL:             https://ai-powered-smart-microgrid-web-app.onrender.com
```

**Frontend — Vercel:**
```
Framework:       Vite
Root directory:  microgrid-ui/
Build command:   npm run build
Output dir:      dist
Production URL:  https://ai-powered-smart-microgrid-web-app.vercel.app
```

**Environment variables (Render):**
`MONGODB_URI`, `SECRET_KEY`, `JWT_SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_TENANT_ID`, `APPLE_CLIENT_ID`, `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY`, `OPENWEATHER_API_KEY`, `MAPBOX_ACCESS_TOKEN`, `FRONTEND_URL`

**Environment variables (Vercel):**
`VITE_FLASK_API_URL`, `VITE_APP_URL`, `VITE_GOOGLE_CLIENT_ID`, `VITE_MICROSOFT_CLIENT_ID`, `VITE_MICROSOFT_TENANT_ID`, `VITE_APPLE_CLIENT_ID`, `VITE_MAPBOX_TOKEN`, `VITE_OPENWEATHER_API_KEY`, `VITE_IPGEO_API_KEY`

### 4.3 Known Limitations and Mitigations

| Limitation | Mitigation |
|-----------|-----------|
| ML `.pkl` files not on Render (gitignored, too large) | Physics-based clearsky fallback in `forecast_routes.py` |
| Render free-tier cold start (30–60 s) | `pingServer()` called on app mount to pre-warm before user logs in |
| ERA5 2017–2021 data gap | Year-analog stochastic resampling (Ch. 3 Step 4) |
| IP geolocation returns Lagos for Nigerian connections | GPS-based reverse geocoding via OSM Nominatim |
| PostgreSQL on Render (needs paid tier) | All production user data uses MongoDB Atlas |

### 4.4 UI Design System

**Theme:** Dark electric — near-void backgrounds, solar amber accents, emerald green secondary.

| Token | Dark mode | Light mode |
|-------|-----------|-----------|
| `--bg-base` | `#080809` | `#F5F5F4` |
| `--bg-card` | `#0F0F14` | `#FFFFFF` |
| `--text-primary` | `#FAFAF9` | `#1C1917` |
| `--primary` | `#F59E0B` | `#D97706` |
| `--accent` | `#10B981` | `#059669` |

**Typography:**
- Display: Rajdhani (headings, logo)
- Body: Inter
- Mono: JetBrains Mono (metrics, timestamps, code)

**Glassmorphism cards:** `backdrop-filter: blur(14px)` + `rgba(15,15,20,0.82)` fill + `1px solid rgba(245,158,11,0.10)` border.

**Responsive:** Desktop sidebar (230 px fixed) + main content. Mobile: sidebar replaced by bottom navigation bar (`<nav className="mobile-nav-bar">`).

---

## Chapter 5 — Testing and Results

### 5.1 Functional Testing Checklist

| Feature | Status | Notes |
|---------|--------|-------|
| Email sign-up + login | ✓ | bcrypt password hash; JWT response |
| Google OAuth | ✓ | Requires production URL in Google Console |
| Microsoft MSAL PKCE | ✓ | Requires production URL in Azure AD |
| Apple Sign In | ✓ | Requires Apple Developer portal setup |
| 4-step onboarding wizard | ✓ | Appliance step saves peak_demand_kw |
| Location detection (GPS) | ✓ | OSM Nominatim; Abuja correctly detected |
| 48-hour forecast (ML) | ✓ | RF/GB/XGBoost side-by-side |
| 48-hour forecast (fallback) | ✓ | Physics-based clearsky when models absent |
| LP battery optimisation | ✓ | PuLP; personalised sizing when appliances set |
| Ensemble anomaly detection | ✓ | Isolation Forest + Z-score + IQR |
| Mapbox globe | ✓ | flyTo animation on country switch |
| Live weather widget | ✓ | OpenWeatherMap |
| Appliance calculator | ✓ | Qty, hours, brand per appliance |
| Nigeria NERC bands | ✓ | A–E selector; rate updates live |
| Country-aware currency | ✓ | ₦/A$/€/C$ per country |
| Printable A4 report | ✓ | @page margins; page-break-inside avoid |
| Light/dark mode | ✓ | CSS variables; persists in localStorage |
| Multilingual support | ✓ | EN/FR/DE/ES/PT/YO |
| Idle session timeout | ✓ | 30 minutes; any interaction resets |
| Mobile responsive | ✓ | Bottom nav bar on small screens |

### 5.2 Bug Log Summary

Key bugs encountered and resolved during development:

| # | Bug | Root cause | Fix |
|---|-----|-----------|-----|
| 1 | Forecast showed "run retrain_models.py" | `.pkl` files gitignored, not on Render | Physics-based synthetic fallback |
| 2 | Location detected Lagos not Abuja | Backend ignored GPS coords; used IP (Lagos ISP node) | OSM Nominatim reverse geocoding |
| 3 | Login "Failed to create user" | `user_routes.py` queried PostgreSQL (not available on Render) | Migrated all queries to MongoDB |
| 4 | OAuth redirect URI mismatch | `window.location.origin` changes per Vercel preview deployment | `VITE_APP_URL` stable production URL in env |
| 5 | Block nested popups (MSAL) | Azure AD redirect URI did not match stable production URL | Same as #4 |
| 6 | Map flyTo wrong location | `flyTo([lat, lon])` — Mapbox expects `[lon, lat]` | Swapped coordinate order |
| 7 | Anomaly 500 error | sklearn convergence warning not caught | Top-level try/except in anomaly route |
| 8 | Sign-out button off screen | Sidebar `overflow: hidden` pushed it below viewport | Wrapped middle section in scrollable flex child |
| 9 | Language switch no effect | Pages imported `useTranslation` instead of `useLanguage` | Replaced all three imports |
| 10 | 830 MB git push rejected | `.git/` folder accidentally committed | Orphan branch rewrite, `.gitignore` fix |
| 11 | Report shows wrong currency for Canada | Hardcoded `₦68/kWh` everywhere | `CURRENCY` map per country; `NIGERIA_BANDS` per band |
| 12 | Report country changes via sidebar | `country = selectedCountry` re-fetched on click | Locked to `profile.country` |
| 13 | PDF cuts off at section 3 | No `@page` or `page-break-inside` CSS | Added proper print CSS |

### 5.3 Performance Notes
- Frontend bundle: Vite production build with manual chunking (vendor, mapbox, charts, pages)
- Backend cold start: 30–60 s on Render free tier; mitigated by pre-warm ping
- ERA5 forecast generation: <2 s for 48-hour window (vectorised numpy operations)
- LP optimisation: <0.5 s for 24-hour schedule (PuLP CBC solver)

---

## Appendix — File Structure

```
AI-Powered-Smart-Microgrid_Web_App/
├── backend/
│   ├── app.py                    # Flask entry point + CORS + blueprint registration
│   ├── requirements.txt          # All runtime dependencies
│   ├── runtime.txt               # python-3.11.9 (Render pin)
│   └── api/
│       ├── auth_routes.py        # Google / Microsoft / Apple / email auth
│       ├── forecast_routes.py    # ML forecast + physics-based fallback
│       ├── optimize_routes.py    # LP battery optimisation
│       ├── anomaly_routes.py     # Ensemble anomaly detection
│       ├── user_routes.py        # User profile CRUD
│       └── location_routes.py    # GPS + IP geolocation
├── database/
│   └── models.py                 # MongoDB User model
├── microgrid-ui/                 # React + Vite frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Onboarding.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── ForecastPage.jsx
│   │   │   ├── OptimizePage.jsx
│   │   │   ├── AnomalyPage.jsx
│   │   │   ├── ReportPage.jsx
│   │   │   └── Settings.jsx
│   │   ├── components/
│   │   │   ├── ApplianceCalculator.jsx  # Load estimator with NERC bands
│   │   │   ├── ForecastChart.jsx
│   │   │   ├── OptimizationChart.jsx
│   │   │   ├── AnomalyPanel.jsx
│   │   │   ├── WeatherWidget.jsx
│   │   │   ├── MapPanel.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── GridBackground.jsx
│   │   ├── context/
│   │   │   ├── AuthContext.jsx          # JWT session + OAuth + idle timeout
│   │   │   └── LanguageContext.jsx      # i18n (EN/FR/DE/ES/PT/YO)
│   │   ├── services/
│   │   │   ├── api.js                   # Axios wrappers + pingServer
│   │   │   └── msalConfig.js            # Microsoft MSAL configuration
│   │   ├── i18n/translations.js
│   │   ├── index.css                    # Design tokens + light/dark theme
│   │   └── main.jsx                     # Theme init + React root
│   └── .env.production                  # Vercel env vars
├── models/
│   ├── retrain_models.py                # Train RF+GB+XGBoost for all countries
│   └── trained/                         # .pkl files (gitignored)
├── data/processed/                      # CSV files (gitignored)
├── WHAT_WAS_DONE.md                     # Step-by-step development log
├── THESIS_CHAPTERS_1_5.md              # This file
└── BUGS_AND_FIXES.md                    # Detailed bug log
```
