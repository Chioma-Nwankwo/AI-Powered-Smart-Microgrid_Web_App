import { useState, useEffect } from 'react';
import Sidebar           from '../components/Sidebar';
import MapPanel          from '../components/MapPanel';
import WeatherWidget     from '../components/WeatherWidget';
import ForecastChart     from '../components/ForecastChart';
import OptimizationChart from '../components/OptimizationChart';
import AnomalyPanel      from '../components/AnomalyPanel';
import GridBackground    from '../components/GridBackground';
import { detectUserCountry, COUNTRIES } from '../services/api';
import { APPLIANCE_CATALOG } from '../components/ApplianceCalculator';
import { useLanguage } from '../context/LanguageContext';
import { Clock, Activity, Zap } from 'lucide-react';

// IANA timezone per country for correct local time display
const COUNTRY_TZ = {
  nigeria:   'Africa/Lagos',
  australia: 'Australia/Sydney',
  germany:   'Europe/Berlin',
  canada:    'America/Toronto',
};

const RATE_NGN = 68;

function EnergyProfileCard({ profile }) {
  const catalog   = APPLIANCE_CATALOG[profile.building_type] ?? APPLIANCE_CATALOG.residential;
  const savedQtys = Object.fromEntries((profile.appliances || []).map(a => [a.id, a.qty]));

  // Top 2 appliances by daily kWh consumption
  const ranked = catalog
    .map(a => ({ ...a, qty: savedQtys[a.id] ?? 0 }))
    .filter(a => a.qty > 0)
    .sort((x, y) => (y.watts * y.qty * y.hours) - (x.watts * x.qty * x.hours))
    .slice(0, 2);

  const monthly_kwh = (profile.daily_kwh || 0) * 30;
  const monthly_ngn = Math.round(monthly_kwh * RATE_NGN);
  const intensity   = profile.peak_demand_kw < 3 ? '#10B981' : profile.peak_demand_kw < 10 ? '#F59E0B' : '#F43F5E';

  return (
    <div style={ep.card} className="fade-up fade-up-3">
      <div style={ep.header}>
        <Zap size={14} color="var(--brown)" />
        <span style={ep.title}>Energy Profile</span>
        <span style={ep.sub}>— based on your appliances</span>
      </div>
      <div style={ep.metrics}>
        <div style={ep.metric}>
          <span style={{ ...ep.metricVal, color: intensity }}>{(profile.peak_demand_kw || 0).toFixed(1)} kW</span>
          <span style={ep.metricLabel}>Peak demand</span>
        </div>
        <div style={ep.divider} />
        <div style={ep.metric}>
          <span style={ep.metricVal}>{(profile.daily_kwh || 0).toFixed(1)} kWh</span>
          <span style={ep.metricLabel}>Daily usage</span>
        </div>
        <div style={ep.divider} />
        <div style={ep.metric}>
          <span style={ep.metricVal}>~₦{monthly_ngn.toLocaleString()}</span>
          <span style={ep.metricLabel}>Est. monthly bill</span>
        </div>
        {ranked.length > 0 && (
          <>
            <div style={ep.divider} />
            <div style={ep.metric}>
              <span style={ep.metricVal}>{ranked.map(a => `${a.icon} ×${a.qty}`).join('  ')}</span>
              <span style={ep.metricLabel}>Top consumers</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const ep = {
  card: {
    background: 'var(--bg-card)', border: '1px solid var(--border)',
    borderRadius: 14, padding: '14px 18px', boxShadow: 'var(--shadow-card)',
  },
  header: { display: 'flex', alignItems: 'center', gap: 7, marginBottom: 12 },
  title:  { fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-display)' },
  sub:    { fontSize: 11, color: 'var(--text-muted)' },
  metrics: { display: 'flex', alignItems: 'center', gap: 0, flexWrap: 'wrap' },
  metric:  { display: 'flex', flexDirection: 'column', gap: 2, padding: '4px 20px 4px 0' },
  metricVal:   { fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' },
  metricLabel: { fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' },
  divider: { width: 1, height: 32, background: 'rgba(255,255,255,0.07)', margin: '0 20px 0 0', flexShrink: 0 },
};

export default function Dashboard({ selectedCountry, onCountryChange }) {
  const { t }   = useLanguage();
  const [clock, setClock] = useState(new Date());

  const profile = (() => {
    try { return JSON.parse(localStorage.getItem('gridai_user') || '{}'); } catch { return {}; }
  })();
  const profileTag = [profile.state, profile.building_type]
    .filter(Boolean)
    .map(v => v.charAt(0).toUpperCase() + v.slice(1))
    .join(' · ');
  const userCenter = (profile.userLng != null && profile.userLat != null)
    ? [profile.userLng, profile.userLat]
    : null;

  // Auto-detect only if no saved profile country exists
  useEffect(() => {
    const stored = JSON.parse(localStorage.getItem('gridai_user') || '{}');
    if (stored.country) return; // respect saved profile
    detectUserCountry().then(detected => {
      if (detected) onCountryChange(detected);
    });
  }, []);

  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const { label, flag } = COUNTRIES[selectedCountry];

  return (
    <div style={s.shell}>
      <GridBackground />
      <Sidebar selectedCountry={selectedCountry} onCountryChange={onCountryChange} />

      <main style={s.main}>
        {/* Top bar */}
        <header style={s.topBar}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Activity size={16} color="var(--primary)" style={{ opacity: 0.8 }} />
            <div>
              <h1 style={s.pageTitle}>
                {flag} {label}
                <span style={s.pageSub}> — {t('microgridOverview')}</span>
              </h1>
              {profileTag && (
                <p style={s.profileTag}>{profileTag}</p>
              )}
            </div>
          </div>
          <div style={s.topRight}>
            <div className="pulse-dot" />
            <span style={s.liveLabel}>{t('live')}</span>
            <div style={s.clockBox}>
              <Clock size={11} color="var(--primary)" style={{ opacity: 0.7 }} />
              <span style={s.clock}>
                {clock.toLocaleTimeString('en-GB', {
                  hour: '2-digit', minute: '2-digit', second: '2-digit',
                  timeZone: COUNTRY_TZ[selectedCountry] ?? undefined,
                })}
              </span>
              <span style={s.tzLabel}>
                {clock.toLocaleTimeString('en-GB', {
                  timeZoneName: 'short',
                  timeZone: COUNTRY_TZ[selectedCountry] ?? undefined,
                }).split(' ').pop()}
              </span>
            </div>
          </div>
        </header>

        {/* Content grid */}
        <div style={s.grid}>

          {/* Row 1: Map + Weather */}
          <div style={s.row1}>
            <div style={{ flex: 1, minHeight: 310 }} className="fade-up fade-up-1">
              <MapPanel selectedCountry={selectedCountry} onCountryChange={onCountryChange} userCenter={userCenter} />
            </div>
            <div style={{ width: 210 }} className="fade-up fade-up-2">
              <WeatherWidget country={selectedCountry} />
            </div>
          </div>

          {/* Row 2: Forecast + Optimization */}
          <div style={s.row2}>
            <div style={{ flex: 1.1 }}>
              <ForecastChart country={selectedCountry} />
            </div>
            <div style={{ flex: 1 }}>
              <OptimizationChart country={selectedCountry} />
            </div>
          </div>

          {/* Row 3: Energy Profile (only shown when appliances configured) */}
          {profile.peak_demand_kw > 0 && (
            <EnergyProfileCard profile={profile} />
          )}

          {/* Row 4: Anomaly full width */}
          <AnomalyPanel country={selectedCountry} />

        </div>
      </main>
    </div>
  );
}

const s = {
  shell: { display: 'flex', height: '100vh', overflow: 'hidden', position: 'relative' },
  main:  { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 },
  topBar: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '11px 20px', borderBottom: '1px solid rgba(245,158,11,0.08)',
    background: 'rgba(15,15,20,0.85)', backdropFilter: 'blur(12px)',
    flexShrink: 0, boxShadow: '0 2px 16px rgba(0,0,0,0.40)',
    position: 'relative', zIndex: 10,
  },
  pageTitle: {
    fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 700,
    color: 'var(--text-primary)', letterSpacing: '0.04em',
  },
  pageSub:     { fontSize: 14, fontWeight: 400, color: 'var(--text-muted)', fontFamily: 'var(--font-body)' },
  profileTag:  { fontSize: 10, color: 'var(--primary)', fontFamily: 'var(--font-mono)', marginTop: 2, letterSpacing: '0.06em', opacity: 0.75 },
  topRight:  { display: 'flex', alignItems: 'center', gap: 10 },
  liveLabel: { fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--green)', letterSpacing: '0.14em', fontWeight: 600 },
  clockBox:  {
    display: 'flex', alignItems: 'center', gap: 6,
    background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.14)',
    borderRadius: 8, padding: '5px 12px', boxShadow: '0 0 10px rgba(245,158,11,0.06)',
  },
  clock:   { fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--primary)', letterSpacing: '0.06em' },
  tzLabel: { fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-muted)', letterSpacing: '0.06em', marginLeft: 2 },
  grid:  { flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 14, padding: 16, position: 'relative', zIndex: 5 },
  row1:  { display: 'flex', gap: 14, minHeight: 310 },
  row2:  { display: 'flex', gap: 14 },
};
