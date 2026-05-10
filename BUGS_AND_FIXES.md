# Bugs, Problems, and Fixes — AI-Powered Smart Microgrid Web App

A running log of every significant problem encountered during development and how each was resolved.

---

## 1. ERA5 Data — NaN at Segment Boundaries

**Problem:** Lag and rolling features (lag_1h, lag_24h, lag_168h, rolling mean/std) were computed per-segment (2008–2016, 2017–2021, 2022–2024) rather than on the full concatenated series. This left NaN values at the join points (e.g. the first 168 rows of each segment).

**Fix:** After concatenating all segments, drop all existing lag/rolling columns and recompute them in a single pass on the full sorted series. Backfill the first 168 rows.

**Script:** `fix_lag_features.py`

---

## 2. Solar MAPE Undefined at Night

**Problem:** MAPE (Mean Absolute Percentage Error) is undefined when actual = 0. Solar radiation is zero every night, so MAPE always produced NaN or divide-by-zero errors.

**Fix:** Use MAE and R² as the primary evaluation metrics for solar forecasting. MAPE is only computed on daytime hours (actual > 0) and noted in the thesis as a conditional metric.

---

## 3. Timezone Offset — Solar Forecast Showed Peaks at Wrong Hour

**Problem:** The solar forecast chart showed peak solar radiation at ~10:00 UTC for Nigeria, but local solar noon is ~12:00 WAT (UTC+1). This made the chart appear to be in UTC while the x-axis labels showed local time, creating a 1-hour visual mismatch.

**Fix:** Added per-country UTC offset lookup to the forecast route. Timestamps in the API response are adjusted to local time before being sent to the frontend.

---

## 4. Solar Forecast Scale — Values in J/m² Instead of W/m²

**Problem:** ERA5 stores solar radiation as accumulated energy in J/m². The model was trained on raw J/m² values (up to ~3,600,000) but the frontend chart expected W/m² (0–1000 range). Charts showed enormous values.

**Fix:** Added unit conversion `ssrd / 3600` (J/m² → W/m²) during feature engineering and enforced it consistently across training data, data_loader, and the forecast API.

---

## 5. LP Optimisation Crashed Without Error Message

**Problem:** The `/api/optimize` endpoint raised unhandled exceptions when the PuLP CBC solver failed (infeasible problem, missing binary, or degenerate input). The frontend received a 500 with no useful body.

**Fix:** Extracted the function body into `_run_optimization()` and wrapped the route in try/except. Returns a structured JSON error with solver status on failure.

---

## 6. Mapbox Globe — `flyTo` Landed in the Ocean

**Problem:** `MapPanel.jsx` called `map.flyTo({ center: [lat, lon] })` but Mapbox expects `[lon, lat]` (longitude first). For Nigeria this sent the map to `[9.08, 7.40]` (near Somalia) instead of Abuja.

**Fix:** Swapped the coordinate order to `[lon, lat]` in all `flyTo` and `setCenter` calls.

---

## 7. Anomaly Detection Showed "Is Flask Running?" Intermittently

**Problem:** The `get_anomalies()` route had no try/except. Any transient error (sparse data, sklearn convergence warning, numpy edge case) propagated as an unhandled 500. The frontend's generic error handler showed "is Flask running?" instead of a real message.

**Fix:** Extracted the route body into `_run_anomalies()` and added a top-level try/except that returns `{error, anomalies: [], n_anomalies: 0}` with HTTP 500, so the real error is visible in logs.

---

## 8. Sidebar Sign-out Button Hidden on Short Viewports

**Problem:** The sidebar used `overflow: hidden` on the outer `<aside>`. When the content (nav, country list, language pills, ML model legend) was taller than the viewport, it pushed the user/sign-out section off the bottom of the screen, where it was clipped.

**Fix:** Wrapped the scrollable middle section in a `<div>` with `flex: 1; overflow-y: auto`. Kept the logo and user section outside the scroll area as sticky header/footer. Removed `overflow: hidden` from the sidebar container.

---

## 9. Email Sign-in — "User Not Found" for New Users

**Problem:** The login page only had a sign-in form. New users clicking "Sign in with email" received a 401 "user not found" from `POST /api/auth/login` and were redirected back to login with no way to register.

**Fix:** Added an `isSignUp` toggle to the email form in `Login.jsx`. New users can switch to "Create account" mode, enter email + password + confirm password, and call `POST /api/auth/signup`. On success they are redirected to the onboarding wizard to complete their profile.

---

## 10. Onboarding Location Detection — Building Type Not Auto-Detected

**Problem:** Users expected "detect my location" to fill in their building type (school, hospital, commercial, etc.). GPS and IP geolocation return coordinates only — there is no API that maps a lat/lon to building purpose.

**Fix:** UX-only change. After detecting country and city, the onboarding wizard auto-advances to the building type selection step. A banner reads "Location found — select your building type on the next step" and a hint below the detect button explains: "Detects your country & city · Building type must be selected manually."

---

## 11. Language Switching Broken on Three Pages

**Problem:** `AnomalyPage.jsx`, `Dashboard.jsx`, and `Onboarding.jsx` were calling `useTranslation()` directly instead of the app's custom `useLanguage()` hook. Language switches had no effect on those pages.

**Fix:** Replaced all `useTranslation()` calls with `useLanguage()` on the affected pages.

---

## 12. Microsoft OAuth — Redirect URI Mismatch

**Problem:** The Microsoft MSAL PKCE flow failed with a redirect URI mismatch error. The Azure App Registration had a Web platform redirect URI, but MSAL in a SPA must use the SPA platform type.

**Fix:** In the Azure portal, deleted the Web platform entry and added `http://localhost:3000` under the SPA platform. MSAL's PKCE flow then matched the registered URI.

---

## 13. Git Push Timeout (HTTP 408) — 830 MB of Accidental `.git` Folder Commits

**Problem:** Every `git push origin main` attempt timed out after ~10 minutes. Root cause: commits `eebdb41` and `e443874` had accidentally committed the entire `.git` folder (830 MB of binary pack files). GitHub rejected pushes over 100 MB.

**Fix:**
1. Added `.git/`, `models/trained/`, `models/saved_models/`, `data/processed/` to `.gitignore`.
2. Created an orphan branch (`git checkout --orphan clean-push`).
3. Ran `git rm -rf --cached .` to unstage everything.
4. Re-added only the 104 source files (no binaries).
5. Made a single clean commit and force-pushed to `main`.

---

## 14. `backend/node_modules/` Accidentally Tracked

**Problem:** During the clean-push process, `backend/node_modules/` (thousands of files) was about to be re-added to git because it was not listed in `.gitignore`.

**Fix:** Added `backend/node_modules/` to `.gitignore` before the clean commit.

---

## 15. Render Deployment — Python 3.14 Incompatible with Several Packages

**Problem:** Render defaulted to Python 3.14.3 (the latest available). Many packages (`authlib`, `tensorflow`, `scipy`, `cryptography`) either lack binary wheels for 3.14 or have known compatibility issues.

**Fix:** Added `backend/runtime.txt` containing `python-3.11.9` to pin the deployment to Python 3.11, which has stable wheels for all required packages.

---

## 16. Render Deployment — Missing Packages in `backend/requirements.txt`

**Problem:** The `backend/requirements.txt` was created with only Flask/CORS/JWT/dotenv/pulp. All other packages (`bcrypt`, `python-jose`, `google-auth`, `authlib`, `cryptography`, `scipy`, `plotly`, `pymongo`, `psycopg2-binary`, `scikit-learn`, `xgboost`, etc.) were only installed in the local venv and not listed. Render created a fresh virtual environment and failed with `ModuleNotFoundError` on each missing package, one at a time per deploy.

**Fix:** Rewrote `backend/requirements.txt` to explicitly list every package required at runtime, grouped by purpose (Flask core, Auth, Database, ML, Optimisation, Visualisation, Utilities).

---

## 17. Render Deployment — tensorflow Import at App Startup

**Problem:** `backend/api/anomaly_routes.py` had a top-level `from models.anomaly_detection import (...)`. That file imports `from tensorflow import keras`. tensorflow is not listed in requirements (it's 500 MB+, not needed for the running app), so the import crashed gunicorn before any routes loaded.

**Fix:** Wrapped the `from models.anomaly_detection import (...)` in a `try/except Exception` block. The main anomaly GET endpoint uses sklearn directly and is unaffected; the unused `/train` and `/detect` endpoints degrade gracefully if tensorflow is absent.

---

## 18. CORS — Frontend Blocked After Vercel Deployment

**Problem:** `app.py` hardcoded `origins=['http://localhost:3000']`. After deploying the frontend to Vercel, all API calls from the Vercel domain were blocked with CORS errors.

**Fix:** Updated `app.py` to read `FRONTEND_URL` from the environment variable and append it to the allowed origins list at startup.

---

## 19. Deployed Environment Variables — OAuth Redirect URIs Still Pointed to localhost

**Problem:** `GOOGLE_REDIRECT_URI` and `MICROSOFT_REDIRECT_URI` in the Render environment still contained `http://localhost:5000/...` callback URLs. OAuth flows from the deployed app would redirect back to a machine that doesn't exist.

**Fix (pending):** Update these values in the Render dashboard to use the deployed backend URL (`https://ai-powered-smart-microgrid-web-app.onrender.com/api/auth/.../callback`) and register the same URIs in Google Cloud Console and Azure Portal.

---

## 20. GitHub Contributors Showed Claude as Co-Author

**Problem:** Claude Code's default commit template adds `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`, which GitHub reads to display Claude as a repository contributor.

**Fix:** Ran `git filter-branch --msg-filter 'sed "/^Co-Authored-By:/d"...' -- --all` to strip Co-Authored-By lines from all commit messages, then force-pushed. GitHub contributor graphs re-cache within a few hours of the force push.

---

*Last updated: 2026-05-02*
