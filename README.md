# AI-Powered Smart Microgrid Web Application
App Link: https://ai-powered-smart-microgrid-web-app.vercel.app/login

**Final Year Project — Nile University of Nigeria**  
Chioma Nwankwo · B.Sc. Computer Science

---

## Overview

A full-stack AI-powered analytics platform for smart microgrid energy management. The system forecasts solar irradiance and wind speed using ERA5-trained machine learning models, optimises battery dispatch using linear programming, and detects grid anomalies using an unsupervised ensemble. It supports four countries (Nigeria, Australia, Germany, Canada) and six languages.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 (JSX) + Vite 7 |
| Backend | Flask 3 (Python 3.10+) |
| Database | MongoDB Atlas (cloud) |
| ML Forecasting | Scikit-Learn — Random Forest, Gradient Boosting, XGBoost |
| Climate Data | ERA5 reanalysis (ECMWF) via CDS API |
| Optimisation | PuLP (CBC MILP solver) |
| Anomaly Detection | Isolation Forest + PCA Reconstruction + One-Class SVM |
| Map | Mapbox GL JS (globe projection) |
| Weather | OpenWeatherMap API (live) |
| Authentication | Flask-JWT-Extended · Google OAuth · Microsoft MSAL (PKCE) · Email/password |
| Geolocation | Browser GPS + IPGeolocation API fallback |

---

## Features

### Dashboard
- Live clock per country timezone (Africa/Lagos, Australia/Sydney, Europe/Berlin, America/Toronto)
- Interactive Mapbox globe — click countries to switch region; flies to capital marker
- Building profile tag (state · building type) pulled from onboarding
- Live weather widget (temperature, cloud cover, wind speed from OpenWeatherMap)

### 48-Hour Energy Forecast
- Three ML models (RF, GB, XGBoost) trained per country on ERA5 solar irradiance and wind speed
- Per-country demand profiles with realistic load shapes (Nigeria: evening AC peak; Australia: afternoon AC; Germany: flat industrial; Canada: morning heating)
- Solar clearsky floor correction for ERA5 de-accumulation artefacts (only applied when model < 12% of clearsky)
- Interactive Recharts line chart — toggle individual models on/off

### Battery Optimisation
- LP battery dispatch (PuLP/CBC) for every forecast hour
- Building-type-aware sizing: residential 15 kWh/8 kW → hospital 200 kWh/100 kW
- Greedy fallback if CBC solver is unavailable
- Recharts bar chart showing charge/discharge/grid schedule

### Anomaly Detection
- Ensemble: Isolation Forest + PCA Reconstruction + One-Class SVM, fitted in-memory on 14-day historical window
- Majority vote (≥ 2/3 detectors) flags an event
- Severity classification: low / medium / high / critical
- Variable attribution (solar irradiance vs. wind speed vs. demand)
- Autoencoder planned (Chapter 3.6)

### Multi-Country & Multi-Language Support
- Countries: 🇳🇬 Nigeria · 🇦🇺 Australia · 🇩🇪 Germany · 🇨🇦 Canada
- Languages: English · Deutsch · Français · Hausa · Yoruba · Igbo (country-contextual)
- Country selection updates forecasts, map, weather, language options, and timezone clock

### Onboarding Flow
- Step 1 — Location: country + state/region picker with GPS + IP geolocation detect button
- Step 2 — Building type: residential, commercial, industrial, school, hospital
- Step 3 — Building details: type-specific fields (institution name, floor area, peak demand, etc.)
- Profile stored in MongoDB; map flies to user's state after login

### Authentication
- Google OAuth (ID token → Flask verify → JWT)
- Microsoft OAuth (MSAL PKCE popup → Flask verify → JWT)
- Email sign-up: creates account with placeholder profile, routes to onboarding
- Email sign-in: JWT session, 30-minute idle timeout auto-logout
- New users always land on onboarding before the dashboard

---

## Project Structure

```
AI-Powered-Smart-Microgrid_Web_App/
├── backend/
│   ├── app.py                      # Flask entry point, CORS, JWT, blueprints
│   ├── config.py                   # Environment config, country rates
│   ├── model_loader.py             # Load/cache trained .pkl models per country
│   ├── data_loader.py              # ERA5 CSV loader with caching
│   ├── api/
│   │   ├── auth_routes.py          # /api/auth — signup, login, Google, Microsoft
│   │   ├── forecast_routes.py      # /api/forecast — 48-hour multi-model forecast
│   │   ├── optimize_routes.py      # /api/optimize — LP battery dispatch
│   │   ├── anomaly_routes.py       # /api/anomaly — ensemble anomaly detection
│   │   ├── user_routes.py          # /api/user — profile CRUD
│   │   └── location_routes.py      # /api/location/detect — GPS/IP geolocation
│   ├── auth/
│   │   ├── user_manager.py         # MongoDB user CRUD
│   │   ├── oauth_handler.py        # Google/Microsoft token verification
│   │   └── password_handler.py     # bcrypt hashing, strength validation
│   ├── models/
│   │   ├── anomaly_detection.py    # IF, PCA, OCSVM, Autoencoder classes
│   │   └── trained/                # .pkl files per country (gitignored)
│   └── requirements.txt
│
└── microgrid-ui/
    ├── src/
    │   ├── App.jsx                 # Routes, country state, needsOnboarding logic
    │   ├── main.jsx                # AuthProvider, GoogleOAuthProvider, LanguageProvider
    │   ├── context/
    │   │   ├── AuthContext.jsx     # Google, Microsoft, email login/signup, JWT session
    │   │   └── LanguageContext.jsx # Language state, t() translation function
    │   ├── pages/
    │   │   ├── Login.jsx           # OAuth buttons + email sign-in/sign-up toggle
    │   │   ├── Onboarding.jsx      # 3-step wizard (location, building, details)
    │   │   ├── Dashboard.jsx       # Map + Weather + Forecast + Optimisation + Anomaly
    │   │   ├── ForecastPage.jsx    # Full-page forecast with model comparison
    │   │   ├── OptimizePage.jsx    # Full-page battery dispatch chart
    │   │   └── AnomalyPage.jsx     # Full-page anomaly list + ensemble methodology
    │   ├── components/
    │   │   ├── Sidebar.jsx         # Nav, country selector, language pills, sign-out
    │   │   ├── MapPanel.jsx        # Mapbox globe, country fills, capital markers
    │   │   ├── ForecastChart.jsx   # Recharts multi-model line chart
    │   │   ├── OptimizationChart.jsx # Recharts battery dispatch bar chart
    │   │   ├── AnomalyPanel.jsx    # Anomaly event cards with severity badges
    │   │   ├── WeatherWidget.jsx   # Live OpenWeatherMap card
    │   │   └── GridBackground.jsx  # Animated amber grid overlay
    │   ├── services/
    │   │   ├── api.js              # Axios instance, all API calls, JWT interceptors
    │   │   └── msalConfig.js       # MSAL PublicClientApplication (PKCE)
    │   └── i18n/
    │       └── translations.js     # Translation keys for 6 languages
    └── package.json
```

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB Atlas account (free tier works)

### Environment Variables

Create `backend/.env`:
```env
MONGODB_URI=mongodb+srv://<user>:<pass>@cluster.mongodb.net/
MONGODB_DB=microgrid_db
JWT_SECRET_KEY=your-secret-key
GOOGLE_CLIENT_ID=...
AZURE_CLIENT_ID=...
```

Create `microgrid-ui/.env`:
```env
VITE_FLASK_API_URL=http://localhost:5000
VITE_MAPBOX_TOKEN=pk.ey...
VITE_OPENWEATHER_API_KEY=...
VITE_IPGEO_API_KEY=...
VITE_GOOGLE_CLIENT_ID=...
```

### Run Locally

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
python app.py
```

**Frontend:**
```bash
cd microgrid-ui
npm install
npm run dev
```

App opens at `http://localhost:5173`

---

## ML Models

Each of the four countries has three trained models per target (solar irradiance, wind speed):

| Model | Key | Notes |
|-------|-----|-------|
| Random Forest | `rf` | Robust baseline, low variance |
| Gradient Boosting | `gb` | Sequential residual correction |
| XGBoost | `xgb` | Default active model |

Models are trained offline on ERA5 hourly reanalysis data (2019–2023) using `train_country_models.py`. Trained `.pkl` files are stored in `models/trained/` (gitignored — too large for GitHub).

**Solar artefact correction:** ERA5 de-accumulated surface solar radiation (`ssrd`) shows near-zero values after UTC 13–14 for tropical/mid-latitude grids. A selective clearsky floor (`_apply_solar_floor`) injects 50% of the astronomical clearsky only when the model prediction falls below 12% of clearsky — preserving real model output during normal hours.

---

## Anomaly Detection Ensemble

Three unsupervised detectors are fitted in-memory at request time on a 14-day ERA5 historical window:

1. **Isolation Forest** — randomly partitions the feature space; shallow splits flag anomalies
2. **PCA Reconstruction** — residuals > 3σ of reconstruction error flag anomalies
3. **One-Class SVM** — RBF kernel hypersphere; points outside boundary are anomalies

An event is flagged when ≥ 2/3 detectors agree (majority vote). Severity is determined by vote fraction and deviation magnitude.

---

## Key Design Decisions

- **No pre-trained anomaly models stored** — detectors are fitted on demand using recent historical data, so thresholds stay calibrated to current grid behaviour without requiring a training pipeline
- **Selective solar floor** — instead of always boosting solar to a high fraction of clearsky, the fix only activates for the known ERA5 artefact zone (< 12% of clearsky), preserving the model's real predictions otherwise
- **Per-country demand profiles** — each country has a Gaussian-shaped load curve tuned to its grid behaviour (Nigeria evening AC peak, Canada morning heating, etc.) with a deterministic random seed so the chart doesn't jump on refresh
- **MSAL PKCE flow** — Microsoft login uses `PublicClientApplication` (SPA platform) rather than the Web platform, which avoids the AADSTS70002 `client_secret` requirement
- **CBC fallback** — if the PuLP CBC solver is not in PATH (common on Windows), the LP solver exception is caught and a greedy dispatch algorithm runs instead

---

## License

Academic project — All Rights Reserved  
© 2025 Chioma Nwankwo, Nile University of Nigeria
