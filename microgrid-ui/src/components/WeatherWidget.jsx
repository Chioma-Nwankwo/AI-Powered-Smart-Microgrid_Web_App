import { useState, useEffect } from 'react';
import { Wind, Droplets, Cloud, MapPin } from 'lucide-react';
import { getWeather, COUNTRIES } from '../services/api';
import { useLanguage } from '../context/LanguageContext';
import useUnits from '../hooks/useUnits';

const WX_ICONS = {
  Clear: '☀️', Clouds: '☁️', Rain: '🌧️',
  Drizzle: '🌦️', Thunderstorm: '⛈️', Snow: '❄️',
  Mist: '🌫️', Haze: '🌫️', Fog: '🌫️',
};

export default function WeatherWidget({ country }) {
  const { t } = useLanguage();
  const { tempStr, windStr } = useUnits();
  const [wx,      setWx]      = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    getWeather(country)
      .then(data => { if (!cancelled) setWx(data); })
      .catch(() => { if (!cancelled) setError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [country]);

  const { flag, capital, label } = COUNTRIES[country];

  if (loading) return (
    <div style={s.card}>
      <div className="skeleton" style={{ height: 120, borderRadius: 10 }} />
    </div>
  );

  if (error || !wx) return (
    <div style={s.card}>
      <p style={s.label}>{t('weather')}</p>
      <div style={s.locationRow}>
        <MapPin size={11} color="var(--text-muted)" />
        <span style={s.locationText}>{capital}, {label}</span>
      </div>
      <div style={s.unavail}>
        <span style={{ fontSize: 28 }}>🌤️</span>
        <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 8 }}>{t('unavailable')}</p>
        <p style={{ color: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)', marginTop: 2 }}>{t('checkApiKey')}</p>
      </div>
    </div>
  );

  const main      = wx.weather?.[0]?.main ?? '—';
  const desc      = wx.weather?.[0]?.description ?? '';
  const tempC     = wx.main?.temp ?? 0;
  const feelsC    = wx.main?.feels_like ?? 0;
  const humidity  = wx.main?.humidity ?? '—';
  const windMps   = wx.wind?.speed ?? 0;
  const clouds    = wx.clouds?.all ?? '—';
  const emoji     = WX_ICONS[main] ?? '🌤️';

  return (
    <div style={s.card}>
      <div style={s.header}>
        <span style={s.label}>{t('weather')}</span>
      </div>

      <div style={s.locationRow}>
        <MapPin size={11} color="var(--text-muted)" />
        <span style={s.locationText}>{capital}, {label}</span>
      </div>

      <div style={s.mainRow}>
        <span style={s.emoji}>{emoji}</span>
        <div>
          <span style={s.temp}>{tempStr(tempC)}</span>
          <p style={s.desc}>{desc}</p>
          <p style={s.feelsLike}>{t('feelsLike')} {tempStr(feelsC)}</p>
        </div>
      </div>

      <div style={s.statsGrid}>
        <Stat icon={<Droplets size={11} color="var(--text-muted)" />} label={t('humidity')}  value={`${humidity}%`} />
        <Stat icon={<Wind     size={11} color="var(--text-muted)" />} label={t('wind')}      value={windStr(windMps)} />
        <Stat icon={<Cloud    size={11} color="var(--text-muted)" />} label={t('cloud')}     value={`${clouds}%`} />
      </div>
    </div>
  );
}

function Stat({ icon, label, value }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        {icon}
        <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>{label}</span>
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-secondary)', fontWeight: 600 }}>{value}</span>
    </div>
  );
}

const s = {
  card: {
    background: 'var(--bg-card)', border: '1px solid var(--border)',
    borderRadius: 14, padding: '16px 18px', height: '100%',
    boxShadow: 'var(--shadow-card)',
  },
  header:      { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  label:       { fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.10em', fontWeight: 600 },
  locationRow: { display: 'flex', alignItems: 'center', gap: 4, marginBottom: 14 },
  locationText:{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 },
  mainRow:     { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 },
  emoji:       { fontSize: 32 },
  temp:        { fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 600, color: 'var(--brown)', lineHeight: 1 },
  desc:        { fontSize: 11, color: 'var(--text-muted)', marginTop: 4, textTransform: 'capitalize' },
  feelsLike:   { fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 2 },
  statsGrid:   { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, borderTop: '1px solid var(--border)', paddingTop: 12 },
  unavail:     { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '16px 0' },
};
