import Sidebar         from '../components/Sidebar';
import ForecastChart   from '../components/ForecastChart';
import WeatherWidget   from '../components/WeatherWidget';
import GridBackground  from '../components/GridBackground';
import { COUNTRIES }   from '../services/api';
import { useLanguage } from '../context/LanguageContext';
import { TrendingUp }  from 'lucide-react';

export default function ForecastPage({ selectedCountry, onCountryChange }) {
  const { t } = useLanguage();
  const { label, flag } = COUNTRIES[selectedCountry];

  return (
    <div style={s.shell}>
      <GridBackground />
      <Sidebar selectedCountry={selectedCountry} onCountryChange={onCountryChange} />

      <main style={s.main}>
        <header style={s.topBar}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <TrendingUp size={18} color="var(--brown)" />
            <div>
              <h1 style={s.pageTitle}>
                {flag} {label}
                <span style={s.pageSub}> — {t('forecastOverview')}</span>
              </h1>
              <p style={s.pageDesc}>ML model comparison · Random Forest, Gradient Boosting, XGBoost</p>
            </div>
          </div>
          <div style={s.topRight}>
            <div className="pulse-dot" />
            <span style={s.liveLabel}>{t('live')}</span>
          </div>
        </header>

        <div style={s.content}>
          {/* Full-width weather strip */}
          <div style={s.weatherStrip}>
            <WeatherWidget country={selectedCountry} />
          </div>

          {/* Forecast chart — expanded */}
          <div style={s.chartWrap}>
            <ForecastChart country={selectedCountry} />
          </div>

          {/* Model info cards */}
          <div style={s.infoRow}>
            {[
              { key: 'RF',  name: 'Random Forest',     color: '#1A7A3F', desc: 'Ensemble of decision trees trained on lag features, hour-of-day, and month. Robust to outliers and missing values.' },
              { key: 'GB',  name: 'Gradient Boosting', color: '#2471A3', desc: 'Sequential tree boosting that minimises residual errors. Captures non-linear interactions between weather variables.' },
              { key: 'XGB', name: 'XGBoost',           color: '#C8793F', desc: 'Regularised gradient boosting with built-in L1/L2 penalties. Generally achieves the lowest RMSE on held-out test data.' },
            ].map(m => (
              <div key={m.key} style={{ ...s.infoCard, borderTop: `3px solid ${m.color}` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 7 }}>
                  <span style={{ ...s.modelBadge, background: m.color }}>{m.key}</span>
                  <span style={s.modelName}>{m.name}</span>
                </div>
                <p style={s.modelDesc}>{m.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

const s = {
  shell: { display: 'flex', height: '100vh', overflow: 'hidden' },
  main:  { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0, background: 'var(--bg-base)' },
  topBar: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '12px 20px', borderBottom: '1px solid var(--border)',
    background: 'var(--bg-card)', flexShrink: 0, boxShadow: 'var(--shadow-up)',
  },
  pageTitle: { fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.02em' },
  pageSub:   { fontSize: 14, fontWeight: 400, color: 'var(--text-muted)', fontFamily: 'var(--font-body)' },
  pageDesc:  { fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 2, letterSpacing: '0.06em' },
  topRight:  { display: 'flex', alignItems: 'center', gap: 10 },
  liveLabel: { fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--green)', letterSpacing: '0.10em', fontWeight: 600 },
  content:   { flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 14, padding: 16 },
  weatherStrip: { alignSelf: 'flex-start' },
  chartWrap: { flex: 1 },
  infoRow: { display: 'flex', gap: 12 },
  infoCard: {
    flex: 1, background: 'var(--bg-card)', border: '1px solid var(--border)',
    borderRadius: 12, padding: '14px 16px', boxShadow: 'var(--shadow-card)',
  },
  modelBadge: {
    fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
    color: '#fff', padding: '2px 8px', borderRadius: 100, letterSpacing: '0.06em',
  },
  modelName: { fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' },
  modelDesc: { fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.6 },
};
