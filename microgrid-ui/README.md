# GridAI — Smart Microgrid Analytics Dashboard

React + Vite frontend for the AI-Powered Smart Microgrid Analytics project.

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Set up environment variables
cp .env.example .env
# → Open .env and fill in all your API keys

# 3. Make sure Flask is running on port 5000
# (in your backend directory: flask run or python app.py)

# 4. Start the frontend
npm run dev
# → Opens at http://localhost:3000
```

## Environment Variables (.env)

| Variable | Where to get it |
|---|---|
| `VITE_FLASK_API_URL` | Your Flask backend URL (default: http://localhost:5000) |
| `VITE_MAPBOX_TOKEN` | https://account.mapbox.com/access-tokens/ |
| `VITE_OPENWEATHER_API_KEY` | https://openweathermap.org/api |
| `VITE_IPGEO_API_KEY` | https://ipgeolocation.io/ |
| `VITE_GOOGLE_CLIENT_ID` | https://console.cloud.google.com → APIs & Services → Credentials |
| `VITE_MICROSOFT_CLIENT_ID` | https://portal.azure.com → App registrations |
| `VITE_MICROSOFT_TENANT_ID` | Same Azure App registration page |

## Flask API Endpoints Expected

The frontend calls these endpoints on your Flask backend:

| Method | Endpoint | Params |
|---|---|---|
| POST | `/api/auth/google` | `{ token }` |
| POST | `/api/auth/microsoft` | `{ token }` |
| GET | `/api/forecast` | `country`, `hours` |
| GET | `/api/optimize` | `country`, `battery_capacity_kwh` |
| GET | `/api/anomaly` | `country`, `hours` |

Expected response shapes are documented in `src/services/api.js`.

## Continuing with Claude Code in VS Code

Claude Code lets you continue building this project with AI assistance
directly in VS Code's terminal — it reads your entire codebase automatically.

```bash
# In VS Code terminal:
npm install -g @anthropic-ai/claude-code

# Navigate to this project folder
cd path/to/microgrid-ui

# Start Claude Code
claude
```

Then just describe what you want to change or add, and it will
understand the full context of all files in this project.

## Project Structure

```
src/
  services/
    api.js          ← All Flask + OpenWeather + IPGeo API calls
    msalConfig.js   ← Microsoft OAuth configuration
  context/
    AuthContext.jsx ← Google + Microsoft auth state
  pages/
    Login.jsx       ← OAuth login page
    Dashboard.jsx   ← Main dashboard layout
  components/
    Sidebar.jsx         ← Navigation + country selector
    MapPanel.jsx        ← Mapbox filled map
    WeatherWidget.jsx   ← OpenWeather current conditions
    ForecastChart.jsx   ← 48h forecast (solar/wind/demand)
    OptimizationChart.jsx ← Battery dispatch schedule
    AnomalyPanel.jsx    ← Anomaly detection events
  App.jsx           ← Routes + auth guard
  main.jsx          ← Entry point with all providers
  index.css         ← Design system (CSS variables + utilities)
```

## Build for Production

```bash
npm run build
# Output goes to /dist — deploy this folder to any static host
# (Netlify, Vercel, AWS S3, etc.)
```
