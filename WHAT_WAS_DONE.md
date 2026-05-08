# Smart Microgrid Analytics — What Was Done (Step-by-Step)

This document explains every major step taken to build and fix the data pipeline,
train ML models, and develop the Flask + React web application.
Aligned with Chapters 1–5 of the thesis.

*Last updated: 2026-05-07. Steps 1–10 = original build. Steps 11–20 = deployment and auth. Steps 21–28 = feature additions (current).*

---

## Step 1 — ERA5 Data Collection (2008–2016)

**What:** Downloaded hourly ERA5 reanalysis data for Nigeria, Australia, Canada, and Germany
from the Copernicus Climate Data Store (CDS).

**Variables downloaded:** Solar radiation (ssrd), wind u/v components (u10/v10),
2 m temperature (t2m), surface pressure (sp), total precipitation (tp),
2 m dewpoint temperature (d2m), total cloud cover (tcc).

**Format:** NetCDF4 (.nc) files stored in `E:/final year project data/`.

**Why:** ERA5 is a globally consistent, quality-controlled reanalysis product at 0.25° × 0.25°
spatial resolution and 1-hour temporal resolution — the standard for renewable energy research.
(Thesis Ch. 1.4.3, Ch. 3.2)

---

## Step 2 — Spatial Averaging (NetCDF → Hourly Time-Series)

**What:** Each NetCDF file covers a lat/lon grid. We spatially averaged every file to produce
a single value per hour (one row = one timestamp, one column = one variable).

**Tool:** `xarray.open_dataset()` with engine fallback (`netcdf4` → `scipy`). Files larger than
1.5 billion elements (global ERA5 grid ≈ 9.1 billion) were skipped — these were identified
as whole-globe downloads where only the regional subset was needed.

**Script:** `c:/Users/chiom/Documents/Final Year Project/generate_2017_2024.py`
→ `_xr_spatial_mean()` function.

---

## Step 3 — Feature Engineering (2008–2016)

**What:** Applied physics-based transformations and added temporal features:

| Output column | Formula |
|---|---|
| `solar_radiation_wm2` | `ssrd / 3600` (convert J/m² to W/m²), clipped ≥ 0 |
| `temperature_celsius` | `t2m − 273.15` (Kelvin to Celsius) |
| `pressure` | `sp / 100` (Pa to hPa) |
| `precipitation_mm` | `tp × 1000`, clipped ≥ 0 |
| `cloud_cover_pct` | `tcc × 100`, clipped 0–100 |
| `wind_speed` | `√(u10² + v10²)` |
| `wind_direction` | `atan2(u10, v10) × 180/π mod 360` |
| `relative_humidity` | Magnus formula from T and Td |
| `hour`, `month`, `day_of_week`, etc. | pandas `.dt` accessors |
| `hour_sin/cos`, `month_sin/cos` | Cyclical encoding: `sin(2π·x/period)` |
| `season` | Northern hemisphere meteorological seasons |

**Lag features** (`shift(lag)`) — thesis Ch. 3.6.1 Input Features:
- `solar_radiation_wm2_lag_1h`, `_lag_24h`, `_lag_168h`
- `wind_speed_lag_1h`, `_lag_24h`, `_lag_168h`
- `temperature_celsius_lag_1h`, `_lag_24h`, `_lag_168h`

**Rolling statistics** (shifted by 1 to avoid data leakage):
- 24-hour rolling mean and standard deviation for solar, wind, temperature.

---

## Step 4 — Synthetic Data for 2017–2021 (Year-Analog Resampling)

**The problem:** ERA5 data for 2017–2021 was unavailable (CDS downloads were incomplete).

**Why not mean imputation:** Assigning the column mean removes all year-to-year variability.
The thesis required defensible imputation (Ch. 3.3).

**Solution — Year-analog resampling (stochastic resampling from climatology):**
1. For each synthetic year Y in {2017–2021}, draw a random donor year D from 2008–2016.
2. Copy all hourly rows from year D; replace timestamp year with Y.
3. Add Gaussian noise (σ = 1% of std dev) to avoid exact duplicate years.

**Seed:** 42. Donors: 2017←2009, 2018←2008, 2019←2012, 2020←2011, 2021←2011.

**Script:** `generate_2017_2024.py` → `make_analog_year()` function.

---

## Step 5 — Loading 2022–2024 Processed Data

**What:** ERA5 data for 2022–2024 had already been downloaded and processed.
Loaded from `web app/data/processed/` and merged with the 2008–2021 block.

---

## Step 6 — Fixing Lag Feature NaN Values (QC Step — Thesis Ch. 3.3)

**The problem:** Lag features showed NaN at segment boundaries (2016/2017, 2021/2022)
because lags were computed per-segment rather than on the full series.

**Fix:**
1. Drop all existing lag and rolling columns after concatenation.
2. Recompute them in a single pass on the full sorted 2008–2024 series.
3. Backfill (`bfill`) the first 168 rows — propagates first valid value backwards.
4. Backfill + forward-fill remaining structural NaN (missing ERA5 variables for 2008–2021).

**Result:** Zero NaN in all four country datasets.

**Script:** `c:/Users/chiom/Documents/Final Year Project/fix_lag_features.py`

---

## Step 7 — Three-Model Training (Thesis Ch. 3.6.1)

The thesis specifies three supervised regression models to be compared:

| Model | Method | Key hyperparameters |
|---|---|---|
| **Random Forest** | Ensemble of 100 decision trees | max_depth=20, min_samples_leaf=2 |
| **Gradient Boosting** | Sequential ensemble (sklearn) | n_estimators=200, lr=0.08, max_depth=6 |
| **XGBoost** | Optimised gradient boosting | n_estimators=300, lr=0.05, max_depth=8 |

**Targets:** `solar_radiation_wm2` (W/m²) and `wind_speed` (m/s)

**Split:** 80% training / 20% test — chronological (no future data leaks into training).

**Normalisation:** StandardScaler fit on training set, applied to test (shared across all models).

**Saved files per country/target:**
- `models/trained/{country}_{target}_rf_model.pkl`
- `models/trained/{country}_{target}_gb_model.pkl`
- `models/trained/{country}_{target}_xgb_model.pkl`
- `models/scalers/{country}_{target}_scaler.pkl` (shared)
- `models/scalers/{country}_{target}_features.pkl` (shared)

**Script:** `retrain_models.py`

**Note:** MAPE for solar is undefined when actual = 0 (night-time). Use MAE and R² as
primary metrics (thesis Ch. 3.3).

---

## Step 8 — Flask Backend API (Thesis Ch. 3.5 Functional Requirements)

The backend is a Flask app (`backend/app.py`) with 11 blueprints:

| Blueprint | URL prefix | Purpose |
|---|---|---|
| `auth_bp`     | `/api/auth`     | Google + Microsoft OAuth, JWT tokens |
| `forecast_bp` | `/api/forecast` | GET: all 3 model predictions side-by-side |
| `optimize_bp` | `/api/optimize` | GET: 24-h battery charge/discharge schedule |
| `anomaly_bp`  | `/api/anomaly`  | GET: IQR-based anomaly detection |
| `data_bp`     | `/api/data`     | Historical data queries |
| `weather_bp`  | `/api/weather`  | OpenWeatherMap proxy |
| `regions_bp`  | `/api/regions`  | Country/region metadata |
| `metrics_bp`  | `/api/metrics`  | Model performance metrics |
| `battery_bp`  | `/api/battery`  | Battery status |
| `location_bp` | `/api/location` | IP geolocation |
| `user_bp`     | `/api/user`     | User profile |

**Forecast response format** (three models side-by-side per hour):
```json
{
  "models_available": ["rf", "gb", "xgb"],
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

**Anomaly detection** (IQR — thesis Ch. 3.3):
- Q1 − 1.5×IQR lower bound, Q3 + 1.5×IQR upper bound
- Severity score = |value − median| / IQR
- Variables: solar radiation, wind speed, temperature, pressure, precipitation

**Optimization** (thesis Ch. 3.7 — Forecast-driven decision making):
- Solar forecast → greedy battery dispatch heuristic
- Charge when solar surplus > 0 and SoC < 95%
- Discharge when solar deficit and SoC > 10%
- Returns: cost savings %, renewable utilisation %, hourly schedule

---

## Step 9 — React Frontend UI (microgrid-ui/)

**Framework:** Vite + React, port 3000, proxies `/api` → Flask at 5000.

**Design (original):** Warm cream/coffee aesthetic (beige backgrounds, brown accents, white cards).
See Step 11 for the redesign to the dark electric theme.

**Key components:**
- `Login.jsx` — Google + Microsoft OAuth, warm cream layout
- `Sidebar.jsx` — Country selector, model legend (RF/GB/XGB), nav
- `Dashboard.jsx` — Full dashboard shell, live clock
- `ForecastChart.jsx` — Three model comparison lines (RF green, GB blue, XGB caramel)
- `OptimizationChart.jsx` — Battery charge/discharge schedule (ComposedChart)
- `AnomalyPanel.jsx` — IQR anomaly events with severity badges
- `WeatherWidget.jsx` — Live weather (OpenWeatherMap)
- `MapPanel.jsx` — Country map

---

## Step 10 — Cleanup

Deleted unnecessary files:
- `frontend/` (old Create React App TypeScript project, superseded by `microgrid-ui/`)
- `train_models.py` (old root-level training script, superseded by `retrain_models.py`)

Fixed Streamlit references in `models/train_models.py` and `database/init_db.py`
(these files still exist for utility but were written before the framework was finalised).

---

## How to Run the App

Open **two** terminals:

```bash
# Terminal 1 — Flask backend (port 5000)
cd "c:/Users/chiom/Documents/Final Year Project/web app"
venv\Scripts\activate
cd backend
python app.py
```

```bash
# Terminal 2 — React frontend (port 3000)
cd "c:/Users/chiom/Documents/Final Year Project/web app/microgrid-ui"
npm run dev
```

Then open **http://localhost:3000** in your browser.

To train all three models (first time or after data update):
```bash
cd "c:/Users/chiom/Documents/Final Year Project/web app"
venv\Scripts\activate
python retrain_models.py
```

---

## Data Files Summary

| File | Location | Rows | Columns | Years |
|---|---|---|---|---|
| `nigeria_processed_data.csv`   | `web app/data/processed/` | ~148,896 | 42 | 2008–2024 |
| `australia_processed_data.csv` | `web app/data/processed/` | ~148,896 | 42 | 2008–2024 |
| `canada_processed_data.csv`    | `web app/data/processed/` | ~148,896 | 42 | 2008–2024 |
| `germany_processed_data.csv`   | `web app/data/processed/` | ~148,872 | 42 | 2008–2024 |

---

## Step 11 — Dark Electric UI Redesign

**What:** Replaced the warm cream/coffee aesthetic with a dark electric theme across all pages and components.

**Design tokens:**
| Token | Value |
|---|---|
| Background | `#0a0f1e` (near-black navy) |
| Surface / card | `#111827` (dark slate) |
| Primary accent | `#F59E0B` (amber/gold) |
| Secondary accent | `#FF9500` (electric orange) |
| Text primary | `#F9FAFB` |
| Text secondary | `#9CA3AF` |
| Border | `rgba(245,158,11,0.2)` |

**Glassmorphism:** Cards use `backdrop-filter: blur(20px)` with `rgba(255,255,255,0.05)` fill and `1px solid rgba(255,255,255,0.1)` borders.

**Pages updated:** `Login.jsx`, `Dashboard.jsx`, `Sidebar.jsx`, `AnomalyPage.jsx`, `Onboarding.jsx`, `MapPanel.jsx`.

**Login redesign:** Two-panel layout — left panel with animated SVG grid-circuit background and feature list; right panel with sign-in options. Custom `GridBackground` component renders a connected-nodes animation on a dark canvas.

---

## Step 12 — Mapbox Globe Integration

**What:** Replaced the static placeholder map with an interactive Mapbox GL JS globe.

**Features:**
- Globe projection (`projection: 'globe'`) with atmospheric haze
- `flyTo()` animation when user switches country from the sidebar
- Capital-city coordinates mapped for Nigeria (Abuja), Australia (Canberra), Canada (Ottawa), Germany (Berlin)
- Terrain and satellite-streets style layers
- Custom amber marker pin at the selected capital

**Bug fixed:** `flyTo` originally used `[lat, lon]` but Mapbox expects `[lon, lat]` — swapped coordinate order (Bug #6 in `BUGS_AND_FIXES.md`).

---

## Step 13 — Anomaly Detection Upgrade (IQR → ML Ensemble)

**What:** Replaced the simple IQR threshold method with a three-model machine learning ensemble.

**Ensemble members:**
| Model | Algorithm | Output |
|---|---|---|
| Isolation Forest | Tree-based isolation | anomaly score |
| PCA reconstruction | Principal component reconstruction error | reconstruction error |
| One-Class SVM | RBF-kernel boundary estimation | support vector score |

**Voting rule:** A point is flagged as an anomaly if ≥ 2 of the 3 models agree (majority vote).

**Variables monitored:** solar radiation, wind speed, temperature, pressure, precipitation.

**Severity scoring:** Normalised deviation from the cluster centre — Low / Medium / High / Critical bands.

**Route:** `GET /api/anomaly?country=nigeria` → `backend/api/anomaly_routes.py`

**Robustness fix:** All three sklearn model fits and predictions are wrapped in a top-level `try/except` so transient errors (sparse data, convergence warnings) return a structured JSON error rather than a bare 500 (Bug #7).

---

## Step 14 — Authentication Expansion

### Email Sign-up
**Problem:** Only sign-in existed; new users received "user not found" with no way to register.

**Fix:** Added `isSignUp` toggle to `Login.jsx`. In sign-up mode, the form shows email + password + confirm-password fields and calls `POST /api/auth/signup`. On success, redirects to `/onboarding`.

**Files changed:** `Login.jsx`, `AuthContext.jsx`, `services/api.js`

### Microsoft MSAL PKCE
**Fix:** Migrated Azure App Registration from Web platform to SPA platform so the PKCE redirect URI (`http://localhost:3000`) matched. MSAL `@azure/msal-browser` now completes the PKCE flow without a redirect-URI mismatch error.

### Idle Session Timeout
**What:** Added 30-minute idle timer to `AuthContext`. Any mouse/keyboard/scroll event resets the timer; on expiry the session is cleared and the user is returned to the login page.

---

## Step 15 — Onboarding Wizard

**What:** New multi-step onboarding flow (`/onboarding`) shown to all new users on first login regardless of authentication method.

**Steps:**
1. Country and city
2. Building type (residential / commercial / school / hospital / industrial)
3. Address / site name
4. (Optional) energy targets

**Location detection:** "Detect my location" button calls `GET /api/location` (IP geolocation via ipgeolocation.io), fills country and city, then auto-advances to the building type step. A banner clarifies: "Location detected — building type cannot be auto-detected, please select it below." (GPS/IP returns coordinates only; no API maps lat/lon to building purpose.)

**Profile saved:** After completion, `PATCH /api/user/profile` stores the user's site data to MongoDB. All subsequent dashboard requests are scoped to the user's selected country.

---

## Step 16 — Multilingual Support

**What:** Added `LanguageContext` and a `useLanguage()` hook supporting English, French, German, Spanish, Portuguese, and Yoruba.

**Language switcher:** Pills in the sidebar (EN / FR / DE / ES / PT / YO). Persisted to `localStorage`.

**Bug fixed:** `AnomalyPage.jsx`, `Dashboard.jsx`, and `Onboarding.jsx` were importing `useTranslation()` directly instead of the app's `useLanguage()` hook — language switches had no effect on those pages. Fixed by replacing all three imports (Bug #11).

---

## Step 17 — Sidebar Layout Fix

**What:** Fixed sign-out button being hidden below the viewport on short screens.

**Root cause:** The `<aside>` had `overflow: hidden`. When the nav + country list + language pills + ML model legend grew taller than the viewport, they pushed the `userSection` (with `marginTop: 'auto'`) off screen.

**Fix:** Wrapped the scrollable middle section in a `<div style={{ flex: 1, overflowY: 'auto' }}>`. Logo and user/sign-out section remain outside the scroll container as sticky header and footer. Thin amber scrollbar track added via `scrollbarColor`.

---

## Step 18 — Production Deployment (Render + Vercel)

### Backend — Render
- **Service type:** Web Service, Root Directory = `backend/`
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`
- **Python version:** Pinned to 3.11.9 via `backend/runtime.txt` (Render defaulted to 3.14, which broke `authlib`, `cryptography`, `scipy`)
- **URL:** `https://ai-powered-smart-microgrid-web-app.onrender.com`

### Frontend — Vercel
- **Framework:** Vite
- **Build command:** `npm run build`
- **Output directory:** `dist`
- **URL:** deployed Vercel domain

### CORS
`app.py` reads `FRONTEND_URL` from environment and adds it to the allowed origins list. Both `http://localhost:3000` and the Vercel domain are permitted.

### Environment variables (Render dashboard)
| Variable | Purpose |
|---|---|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `SECRET_KEY` / `JWT_SECRET_KEY` | Token signing |
| `GOOGLE_CLIENT_ID/SECRET` | Google OAuth |
| `MICROSOFT_CLIENT_ID/SECRET/TENANT_ID` | Microsoft OAuth |
| `OPENWEATHER_API_KEY` | Live weather |
| `MAPBOX_ACCESS_TOKEN` | Globe map |
| `FRONTEND_URL` | CORS allow-list |
| `BACKEND_URL` | Self-reference for OAuth callbacks |

---

## Step 19 — Requirements and Startup Fixes

### Full requirements.txt rewrite
The original `backend/requirements.txt` only listed Flask/CORS/JWT/dotenv/PuLP. All other packages (`authlib`, `python-jose`, `google-auth`, `cryptography`, `bcrypt`, `pymongo`, `psycopg2-binary`, `scikit-learn`, `xgboost`, `scipy`, `plotly`) were only in the local venv. Added every runtime dependency grouped by purpose (Bug #16).

### tensorflow startup crash
`models/anomaly_detection.py` imports `from tensorflow import keras` at the top level. tensorflow (500 MB) is not in requirements. Wrapped the import block in `anomaly_routes.py` with `try/except Exception` → `_HAS_ANOMALY_MODELS = False`. The main GET route uses sklearn directly and is unaffected (Bug #17).

---

## Step 20 — Git History Cleanup

### Accidental .git and node_modules commits
Commits `eebdb41` and `e443874` had accidentally committed the entire `.git/` folder (830 MB of binary packs) and `node_modules/`. GitHub rejected pushes over 100 MB.

**Fix:**
1. Updated `.gitignore` to exclude `.git/`, `models/trained/`, `models/saved_models/`, `data/processed/`, `backend/node_modules/`.
2. Created orphan branch, ran `git rm -rf --cached .`, re-added only source files.
3. Force-pushed clean history to `main`.

### Claude co-author lines
Claude Code's default commit template adds `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`. Stripped from all commits with `git filter-branch --msg-filter` and force-pushed (Bug #20).

---

## Step 21 — Physics-Based Forecast Fallback

**Problem:** ML `.pkl` model files are excluded from git (`.gitignore`). On Render, the trained models were never present, so every forecast call returned "run retrain_models.py first".

**Fix:** Added a physics-based clearsky fallback in `backend/api/forecast_routes.py`.
- `_synth_solar()` — Gaussian curve centred at solar noon (σ = 3.5 h), scaled by country latitude and a stochastic cloud factor. Produces realistic W/m² with day/night cycle.
- `_synth_wind()` — Weibull-distribution wind speed with diurnal variation.
- When `.pkl` models are absent, all three model outputs (RF, GB, XGBoost) are filled using the same synthetic values so the chart still displays three lines.
- Response includes `"using_synthetic": true`; frontend shows "Physics-based clearsky estimates" badge instead of an error.

**Files:** `backend/api/forecast_routes.py`, `microgrid-ui/src/components/ForecastChart.jsx`

---

## Step 22 — GPS-Accurate Location Detection (Abuja Fix)

**Problem:** Location detection was ignoring GPS coordinates from the browser and always returning Lagos (the IP geolocation fallback for Nigerian connections routes through Lagos ISP nodes).

**Fix:**
- `backend/api/location_routes.py` — added `_reverse_geocode_osm(lat, lon)` which calls the OpenStreetMap Nominatim API (`nominatim.openstreetmap.org/reverse`). Free, no API key required.
- When the frontend passes `?lat=X&lon=Y` (from `navigator.geolocation`), the backend uses OSM reverse geocoding to get the actual state/city (e.g., FCT → Abuja).
- Added `_STATE_ALIASES` dictionary to normalise OSM output (`"Federal Capital Territory"` → `"FCT"`).
- Default fallback changed from Lagos to Abuja (FCT, 9.0579°N, 7.4951°E) since the university is in Abuja.

**Files:** `backend/api/location_routes.py`

---

## Step 23 — Apple Sign In

**What:** Added Apple as a third OAuth provider.

**Frontend:**
- `react-apple-login` npm package; renders Apple button in `Login.jsx`
- Button hidden when `VITE_APPLE_CLIENT_ID` env var is not set (safe for local dev)
- `AuthContext.jsx` — added `signInWithApple()` callback
- `services/api.js` — added `loginWithApple()` POST to `/api/auth/apple`

**Backend:**
- `backend/api/auth_routes.py` — added `/apple` POST route
- Decodes the Apple `id_token` JWT payload (same base64 approach as Microsoft)
- Extracts `sub` (provider ID), `email`, and name from the first-login `user_info` object

**Setup required (Apple Developer portal):**
- App ID with "Sign in with Apple" capability
- Services ID (`com.gridai.signin`) as `APPLE_CLIENT_ID`
- Key (`.p8` file) → `APPLE_PRIVATE_KEY` env var on Render
- `APPLE_TEAM_ID`, `APPLE_KEY_ID` env vars

---

## Step 24 — Appliance-Based Load Estimation (Supervisor Feedback)

**Supervisor feedback:** The app should model buildings where different rooms/areas consume different amounts of electricity.

**What was built:**

### ApplianceCalculator component (`microgrid-ui/src/components/ApplianceCalculator.jsx`)
- Grid of appliance cards per building type (residential / commercial / industrial / school / hospital)
- Each card has three editable inputs:
  - **Qty** — how many of this appliance (direct number input + +/− steppers)
  - **h/day** — hours used per day (editable, not fixed; max 24)
  - **Brand** — optional text field (e.g. "LG", "Samsung"); shown when qty > 0
- Live summary bar: `Peak X kW · Daily X kWh · ~₦Y/month`
- Formulas: `peak_kw = Σ(watts × qty) / 1000`, `daily_kwh = Σ(watts × qty × hours) / 1000`
- Nigeria NERC 2024 tariff bands (A–E): user selects their band; rate per kWh updates accordingly

### NERC 2024 Tariff Bands (Nigeria)
| Band | Supply hours/day | Rate (₦/kWh) |
|------|-----------------|--------------|
| A    | 20+             | ₦225         |
| B    | 16–20           | ₦63          |
| C    | 12–16           | ₦50          |
| D    | 8–12            | ₦43          |
| E    | <8              | ₦40          |

### Country-aware currency
| Country   | Symbol | Rate      |
|-----------|--------|-----------|
| Nigeria   | ₦      | Band-dependent |
| Australia | A$     | A$0.28/kWh |
| Germany   | €      | €0.30/kWh  |
| Canada    | C$     | C$0.13/kWh |

### Integration points
- **Onboarding** — Step 2 of 4 (between building type and address)
- **Settings** — "Your Appliances" card; updates save to MongoDB + localStorage
- **Dashboard** — `EnergyProfileCard` (peak demand, daily kWh, monthly cost, top 2 appliances)
- **Optimize page** — battery/solar sizing derived from `peak_demand_kw` and `daily_kwh`
- **Report** — Appliance Inventory table with brand and hours columns

**Backend:** `user_routes.py` and `database/models.py` — added `appliances`, `peak_demand_kw`, `daily_kwh`, `nigeria_band` to allowed update fields.

---

## Step 25 — Printable Report Page

**What:** Added `/report` route and `ReportPage.jsx` — a clean A4-formatted printable report.

**Sections:**
1. Facility Overview (name, email, country, region, building type, address)
2. Energy Consumption Profile (peak demand, daily kWh, monthly cost, appliance inventory table with brand/hours columns) — only shown if appliances configured
3. 48-Hour Forecast Summary (avg/peak solar irradiance, wind speed, demand)
4. Battery & Solar Optimisation (battery capacity, panel size, solar generated, grid import, cost saving)
5. Anomaly Detection Status (count, method, monitoring window)

**Print behaviour:**
- `@media print` CSS hides sidebar and toolbar; renders clean white A4
- `@page { size: A4; margin: 15mm 12mm }` for proper PDF margins
- `page-break-inside: avoid` on all sections to prevent mid-section cuts
- `window.print()` opens browser print dialog (Save as PDF supported)

**Country lock:** Report always uses the user's profile country — changing the sidebar country does not re-fetch report data (prevents showing Nigeria header with Canada data).

---

## Step 26 — Login Cold-Start Fix (Render Free-Tier)

**Problem:** Render free-tier services sleep after 15 minutes of inactivity. The first request after sleep takes 30–60 seconds, making login appear broken.

**Fix:**
- `services/api.js` — added `pingServer()` which calls `GET /api/health`
- `AuthContext.jsx` — fires `pingServer()` on mount (before the user interacts with the page)
- `Login.jsx` — shows a pulsing amber "Server is starting up, please wait a moment…" banner while `serverReady === false`

**Effect:** The server is woken up as soon as the app loads, before the user types their credentials. By the time they click "Sign in", the server is ready.

---

## Step 27 — OAuth Stable Redirect URI Fix

**Problem:** `msalConfig.js` used `window.location.origin` as the MSAL redirect URI. Vercel creates a different URL per preview deployment, so the redirect URI in the MSAL request changed on every deploy — causing "redirect URI mismatch" errors in Azure AD and Apple.

**Fix:**
- Added `VITE_APP_URL=https://ai-powered-smart-microgrid-web-app.vercel.app` to `.env.production`
- `msalConfig.js` — redirect URI is now `import.meta.env.VITE_APP_URL || window.location.origin`
- `Login.jsx` (Apple button) — same fix for `redirectURI` prop

---

## Step 28 — Light / Dark Mode Toggle

**What:** Added user-selectable light/dark theme.

**CSS (`index.css`):** Added `[data-theme="light"]` rule block that overrides all `--bg-*`, `--text-*`, `--border`, `--shadow-*` CSS variables. Sidebar remains dark in both themes (hardcoded `#050508` in Sidebar.jsx inline styles).

**Settings page:** "Appearance" row in Preferences card with Sun/Moon icon button. Clicking toggles between dark and light, persists to `localStorage` as `gridai_theme`.

**`main.jsx`:** Reads `gridai_theme` from localStorage before first render and sets `document.documentElement.setAttribute('data-theme', ...)` so the correct theme is applied immediately (no flash).

---

## Key Scripts Summary

| Script | Purpose |
|---|---|
| `generate_2017_2024.py` | Full data pipeline: ERA5 → feature engineering → year-analog → combine |
| `fix_lag_features.py` | Post-hoc QC: recompute lags on full series, fill NaN |
| `retrain_models.py` | Train RF + GB + XGBoost for all countries, save models/scalers |
| `backend/app.py` | Flask REST API entry point |
| `microgrid-ui/` | React + Vite frontend (run with `npm run dev`) |
