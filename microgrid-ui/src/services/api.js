import axios from 'axios';

const BASE_URL = import.meta.env.VITE_FLASK_API_URL || 'http://localhost:5000';
const OW_KEY   = import.meta.env.VITE_OPENWEATHER_API_KEY;
const IPGEO_KEY = import.meta.env.VITE_IPGEO_API_KEY;

// Country capitals for OpenWeather calls
export const COUNTRIES = {
  nigeria:   { label: 'Nigeria',   code: 'NG', iso3: 'NGA', flag: '🇳🇬', capital: 'Abuja',    lat:  9.0765, lon:  7.3986 },
  australia: { label: 'Australia', code: 'AU', iso3: 'AUS', flag: '🇦🇺', capital: 'Canberra', lat: -35.2809, lon: 149.1300 },
  germany:   { label: 'Germany',   code: 'DE', iso3: 'DEU', flag: '🇩🇪', capital: 'Berlin',   lat:  52.5200, lon:  13.4050 },
  canada:    { label: 'Canada',    code: 'CA', iso3: 'CAN', flag: '🇨🇦', capital: 'Ottawa',   lat:  45.4215, lon: -75.6972 },
};

// ── Flask API ────────────────────────────────────────────────────────

const flaskApi = axios.create({ baseURL: BASE_URL });

// Attach JWT on every request
flaskApi.interceptors.request.use(cfg => {
  const token = localStorage.getItem('jwt_token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

// Redirect to login on 401
flaskApi.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('jwt_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// Auth
export const loginWithGoogle       = token            => flaskApi.post('/api/auth/google',    { token });
export const loginWithMicrosoft    = token            => flaskApi.post('/api/auth/microsoft', { token });
export const loginWithEmailPassword = (email, password) => flaskApi.post('/api/auth/login',   { email, password });
export const registerWithEmailPassword = (email, password) => flaskApi.post('/api/auth/signup', {
  email, password,
  country: 'Nigeria', state: 'Not specified',
  building_type: 'residential', address: 'Not specified',
});

// Forecast  — country: 'nigeria' | 'australia' | 'germany' | 'canada'
//           — hours:   how many hours ahead (default 24)
export const getForecast = (country, hours = 24) =>
  flaskApi.get('/api/forecast', { params: { country, hours } });

// Optimization — country + battery_capacity_kwh
export const getOptimization = (country, battery_capacity_kwh = 100, panel_kw = 50) =>
  flaskApi.get('/api/optimize', { params: { country, battery_capacity_kwh, panel_kw } });

// Anomaly detection — country + optional time window
export const getAnomalies = (country, hours = 48) =>
  flaskApi.get('/api/anomaly', { params: { country, hours } });

// ── OpenWeatherMap ───────────────────────────────────────────────────

export const getWeather = async (country) => {
  const { lat, lon, capital } = COUNTRIES[country];
  const res = await axios.get('https://api.openweathermap.org/data/2.5/weather', {
    params: { lat, lon, appid: OW_KEY, units: 'metric' },
  });
  return { ...res.data, capital };
};

// ── IPGeolocation ────────────────────────────────────────────────────

// Returns which of the 4 study countries the user is in, or null
export const detectUserCountry = async () => {
  try {
    const res = await axios.get(
      `https://api.ipgeolocation.io/ipgeo?apiKey=${IPGEO_KEY}`
    );
    const code = res.data?.country_code2?.toLowerCase();
    const match = Object.entries(COUNTRIES).find(
      ([, v]) => v.code.toLowerCase() === code
    );
    return match ? match[0] : null; // e.g. 'nigeria'
  } catch {
    return null;
  }
};
