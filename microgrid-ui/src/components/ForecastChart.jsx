import { useState, useEffect } from 'react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts';
import { TrendingUp, RefreshCw } from 'lucide-react';
import { getForecast } from '../services/api';
import { useLanguage } from '../context/LanguageContext';
import { format } from 'date-fns';

const METRICS = [
  { key: 'solar',  label: 'Solar (W/m²)', unit: 'W/m²' },
  { key: 'wind',   label: 'Wind (m/s)',   unit: 'm/s'  },
  { key: 'demand', label: 'Demand (MW)',  unit: 'MW'   },
];

// UTC offsets per country (standard time; Australia uses AEST UTC+10)
const COUNTRY_UTC_OFFSET = {
  nigeria:   1,
  australia: 10,
  germany:   1,
  canada:   -5,
};

const MODELS = [
  { key: 'rf',  label: 'Random Forest',    color: '#10B981' },
  { key: 'gb',  label: 'Gradient Boosting', color: '#F59E0B' },
  { key: 'xgb', label: 'XGBoost',          color: '#F43F5E' },
];

const DEMAND_COLOR = '#A78BFA';

const CustomTooltip = ({ active, payload, label, unit }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(15,15,20,0.96)', border: '1px solid rgba(245,158,11,0.22)', borderRadius: 10,
      padding: '10px 14px', boxShadow: 'var(--shadow-card)',
      fontFamily: 'var(--font-mono)', fontSize: 11,
    }}>
      <p style={{ color: 'var(--text-muted)', marginBottom: 6 }}>{label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color, marginBottom: 3 }}>
          {p.name}: <strong>{p.value?.toFixed(2)} {unit}</strong>
        </p>
      ))}
    </div>
  );
};

export default function ForecastChart({ country }) {
  const { t } = useLanguage();
  const [data,      setData]      = useState([]);
  const [active,    setActive]    = useState('solar');
  const [available, setAvailable] = useState([]);
  const [synthetic, setSynthetic] = useState(false);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(false);

  const load = () => {
    setLoading(true);
    setError(false);
    getForecast(country, 48)
      .then(({ data: res }) => {
        setAvailable(res.models_available ?? []);
        setSynthetic(res.using_synthetic ?? false);
        const offsetMs = (COUNTRY_UTC_OFFSET[country] ?? 0) * 3_600_000;
        const rows = (res.forecast ?? []).map(row => ({
          time:      format(new Date(new Date(row.timestamp).getTime() + offsetMs), 'HH:mm'),
          solar_rf:  row.solar_rf  != null ? +row.solar_rf.toFixed(1)  : undefined,
          solar_gb:  row.solar_gb  != null ? +row.solar_gb.toFixed(1)  : undefined,
          solar_xgb: row.solar_xgb != null ? +row.solar_xgb.toFixed(1)
                     : row.solar_radiation_wm2 != null ? +parseFloat(row.solar_radiation_wm2).toFixed(1)
                     : undefined,
          wind_rf:   row.wind_rf   != null ? +row.wind_rf.toFixed(2)  : undefined,
          wind_gb:   row.wind_gb   != null ? +row.wind_gb.toFixed(2)  : undefined,
          wind_xgb:  row.wind_xgb  != null ? +row.wind_xgb.toFixed(2)
                     : row.wind_speed != null ? +parseFloat(row.wind_speed).toFixed(2)
                     : undefined,
          demand:    +(row.demand ?? 0).toFixed(2),
        }));
        setData(rows);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [country]);

  const metric    = METRICS.find(m => m.key === active);
  const visModels = active === 'demand' ? [] : MODELS.filter(m => available.includes(m.key));

  return (
    <div style={s.card} className="fade-up fade-up-2">
      {/* Header */}
      <div style={s.header}>
        <div style={s.titleRow}>
          <TrendingUp size={15} color="var(--brown)" />
          <span style={s.title}>{t('forecast48h')}</span>
          <span style={s.subtitle}>— {t('mlComparison')}</span>
        </div>

        <div style={s.controls}>
          {METRICS.map(m => (
            <button
              key={m.key}
              onClick={() => setActive(m.key)}
              style={{ ...s.tab, ...(active === m.key ? s.tabActive : {}) }}
            >
              {m.label.split(' ')[0]}
            </button>
          ))}
          <button onClick={load} style={s.refreshBtn} disabled={loading}>
            <RefreshCw size={12} style={loading ? { animation: 'spin 0.7s linear infinite' } : {}} />
          </button>
        </div>
      </div>

      {/* Model legend badges (when not demand) */}
      {active !== 'demand' && visModels.length > 0 && (
        <div style={s.legendRow}>
          {visModels.map(m => (
            <span key={m.key} style={s.legendTag}>
              <span style={{ ...s.legendDot, background: m.color }} />
              {m.label}
            </span>
          ))}
        </div>
      )}

      {error && <p style={s.errText}>{t('loadFailed')}</p>}

      {loading && !data.length
        ? <div className="skeleton" style={{ height: 210 }} />
        : (
          <ResponsiveContainer width="100%" height={210}>
            <AreaChart data={data} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
              <defs>
                {MODELS.map(m => (
                  <linearGradient key={m.key} id={`grad-${m.key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={m.color} stopOpacity={0.22} />
                    <stop offset="95%" stopColor={m.color} stopOpacity={0}    />
                  </linearGradient>
                ))}
                <linearGradient id="grad-demand" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={DEMAND_COLOR} stopOpacity={0.22} />
                  <stop offset="95%" stopColor={DEMAND_COLOR} stopOpacity={0}    />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} interval={7} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
              <Tooltip content={<CustomTooltip unit={metric.unit} />} />

              {active === 'demand' ? (
                <Area
                  type="monotone"
                  dataKey="demand"
                  name="Demand"
                  stroke={DEMAND_COLOR}
                  strokeWidth={2}
                  fill="url(#grad-demand)"
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ) : (
                visModels.map(m => (
                  <Area
                    key={m.key}
                    type="monotone"
                    dataKey={`${active}_${m.key}`}
                    name={m.label}
                    stroke={m.color}
                    strokeWidth={2}
                    fill={`url(#grad-${m.key})`}
                    dot={false}
                    activeDot={{ r: 4, fill: m.color }}
                    connectNulls
                  />
                ))
              )}
            </AreaChart>
          </ResponsiveContainer>
        )
      }

      {/* Synthetic estimate badge — shown instead of error when no trained models are deployed */}
      {!loading && synthetic && !error && (
        <p style={s.noModel}>Physics-based clearsky estimates (ML models not deployed)</p>
      )}
    </div>
  );
}

const s = {
  card: {
    background: 'var(--bg-card)', border: '1px solid var(--border)',
    borderRadius: 14, padding: '16px 18px', boxShadow: 'var(--shadow-card)',
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: 10, flexWrap: 'wrap', gap: 8,
  },
  titleRow: { display: 'flex', alignItems: 'center', gap: 7 },
  title:    { fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.09em', fontWeight: 600 },
  subtitle: { fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' },
  controls: { display: 'flex', gap: 5, alignItems: 'center' },
  tab: {
    padding: '4px 11px', borderRadius: 7, border: '1px solid var(--border)',
    background: 'transparent', color: 'var(--text-muted)', fontSize: 11,
    fontFamily: 'var(--font-mono)', cursor: 'pointer', transition: 'all 0.15s',
  },
  tabActive: {
    background: 'var(--brown-dim)', color: 'var(--brown)',
    borderColor: 'var(--border-bright)', fontWeight: 600,
  },
  refreshBtn: {
    padding: 5, borderRadius: 7, border: '1px solid var(--border)',
    background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex',
  },
  legendRow: { display: 'flex', gap: 10, marginBottom: 10, flexWrap: 'wrap' },
  legendTag: {
    display: 'flex', alignItems: 'center', gap: 5,
    fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)',
  },
  legendDot: { width: 8, height: 8, borderRadius: '50%' },
  errText:   { color: 'var(--red)', fontSize: 11, fontFamily: 'var(--font-mono)', marginBottom: 8 },
  noModel:   { color: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--font-mono)', textAlign: 'center', padding: '12px 0' },
};
