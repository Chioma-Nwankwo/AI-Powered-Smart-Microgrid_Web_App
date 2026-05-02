# Smart Microgrid Analytics — What Was Done (Step-by-Step)

This document explains every major step taken to build and fix the data pipeline,
train ML models, and develop the Flask + React web application.
Aligned with Chapters 1–3 of the thesis.

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

**Design:** Warm cream/coffee aesthetic (beige backgrounds, brown accents, white cards).

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

## Key Scripts Summary

| Script | Purpose |
|---|---|
| `generate_2017_2024.py` | Full data pipeline: ERA5 → feature engineering → year-analog → combine |
| `fix_lag_features.py` | Post-hoc QC: recompute lags on full series, fill NaN |
| `retrain_models.py` | Train RF + GB + XGBoost for all countries, save models/scalers |
| `backend/app.py` | Flask REST API entry point |
| `microgrid-ui/` | React + Vite frontend (run with `npm run dev`) |
