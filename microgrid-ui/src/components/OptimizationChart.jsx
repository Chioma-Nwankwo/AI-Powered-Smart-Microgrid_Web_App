import { useState, useEffect, useCallback } from 'react';
import {
  ResponsiveContainer, ComposedChart, Bar, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine,
} from 'recharts';
import { Zap, RefreshCw } from 'lucide-react';
import { getOptimization } from '../services/api';

const AUTO_REFRESH_MS = 15 * 60 * 1000; // re-fetch every 15 minutes

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(7,21,37,0.95)', border: '1px solid rgba(0,207,255,0.18)', borderRadius: 10,
      padding: '10px 14px', boxShadow: 'var(--shadow-card)',
      fontFamily: 'var(--font-mono)', fontSize: 11,
    }}>
      <p style={{ color: 'var(--text-muted)', marginBottom: 6 }}>{label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color, marginBottom: 3 }}>
          {p.name}: <strong>{p.value?.toFixed(2)}</strong>
        </p>
      ))}
    </div>
  );
};

const BUILDING_CAPACITY = {
  residential: { battery_kwh: 15,  panel_kw: 8   },
  commercial:  { battery_kwh: 100, panel_kw: 50  },
  industrial:  { battery_kwh: 500, panel_kw: 200 },
  school:      { battery_kwh: 50,  panel_kw: 30  },
  hospital:    { battery_kwh: 200, panel_kw: 100 },
};

export default function OptimizationChart({ country }) {
  const [data,      setData]      = useState([]);
  const [summary,   setSummary]   = useState(null);
  const [solver,    setSolver]    = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(false);
  const [updatedAt, setUpdatedAt] = useState(null);

  const fetch = useCallback(() => {
    setLoading(true);
    setError(false);
    const profile  = JSON.parse(localStorage.getItem('gridai_user') || '{}');
    const btype    = profile.building_type?.toLowerCase() || 'commercial';
    const caps     = BUILDING_CAPACITY[btype] || BUILDING_CAPACITY.commercial;
    getOptimization(country, caps.battery_kwh, caps.panel_kw)
      .then(({ data: res }) => {
        const schedule = res.schedule ?? res.data ?? [];
        const rows = schedule.map(row => ({
          time:      row.hour !== undefined ? `${String(row.hour).padStart(2,'0')}:00` : row.timestamp,
          charge:    parseFloat((row.battery_charge    ?? 0).toFixed(2)),
          discharge: parseFloat((row.battery_discharge ?? 0).toFixed(2)),
          soc:       parseFloat((row.state_of_charge   ?? row.soc ?? 0).toFixed(1)),
          solar:     parseFloat((row.solar_generation  ?? row.solar ?? 0).toFixed(2)),
          load:      parseFloat((row.load              ?? row.demand ?? 0).toFixed(2)),
          grid:      parseFloat((row.grid_import       ?? 0).toFixed(2)),
        }));
        setData(rows);
        setSummary(res.summary ?? null);
        setSolver(res.solver ?? null);
        setUpdatedAt(new Date());
      })
      .catch(err => setError(err?.response?.data?.error || true))
      .finally(() => setLoading(false));
  }, [country]);

  useEffect(() => {
    fetch();
    const id = setInterval(fetch, AUTO_REFRESH_MS);
    return () => clearInterval(id);
  }, [fetch]);

  const updatedLabel = updatedAt
    ? updatedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <div style={s.card} className="fade-up fade-up-3">
      {/* Header */}
      <div style={s.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <Zap size={15} color="var(--caramel, var(--brown))" />
          <span style={s.title}>BATTERY OPTIMIZATION</span>
          <span style={s.subtitle}>— local time · LP/MILP</span>
          {solver && (
            <span style={s.solverBadge}>
              {solver === 'pulp_milp' ? 'PuLP·CBC' : 'greedy'}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {updatedLabel && (
            <span style={s.updatedAt}>updated {updatedLabel}</span>
          )}
          <button onClick={fetch} style={s.refreshBtn} disabled={loading} title="Refresh now">
            <RefreshCw size={12} style={loading ? { animation: 'spin 0.7s linear infinite' } : {}} />
          </button>
          {summary && (
            <div style={s.kpiRow}>
              <KPI label="Cost savings"   value={`${summary.cost_savings_pct?.toFixed(1) ?? '—'}%`} color="var(--green)" />
              <KPI label="RE utilized"    value={`${summary.renewable_utilization_pct?.toFixed(1) ?? '—'}%`} color="var(--brown)" />
            </div>
          )}
        </div>
      </div>

      {error && <p style={s.errText}>{typeof error === 'string' ? error : 'Failed to load optimization — is Flask running?'}</p>}

      {loading && !data.length
        ? <div className="skeleton" style={{ height: 210 }} />
        : (
          <ResponsiveContainer width="100%" height={210}>
            <ComposedChart data={data} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} interval={3} />
              <YAxis yAxisId="power" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
              <YAxis yAxisId="soc" orientation="right" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} domain={[0, 100]} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }} />
              <ReferenceLine yAxisId="power" y={0} stroke="var(--border-bright)" />
              <Bar yAxisId="power" dataKey="charge"    name="Charge (kW)"    fill="#1A7A3F" opacity={0.8} radius={[3,3,0,0]} />
              <Bar yAxisId="power" dataKey="discharge" name="Discharge (kW)" fill="#C8793F" opacity={0.8} radius={[3,3,0,0]} />
              <Line yAxisId="soc"   dataKey="soc"  name="SOC (%)"      stroke="#7B52A8" dot={false} strokeWidth={2} />
              <Line yAxisId="power" dataKey="solar" name="Solar (kW)"   stroke="#D4860A" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
            </ComposedChart>
          </ResponsiveContainer>
        )
      }
    </div>
  );
}

function KPI({ label, value, color }) {
  return (
    <div style={{ textAlign: 'right' }}>
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: 15, fontWeight: 600, color }}>{value}</p>
      <p style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{label}</p>
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
    marginBottom: 12, flexWrap: 'wrap', gap: 8,
  },
  title:   { fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.09em', fontWeight: 600 },
  subtitle: { fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', marginLeft: 2 },
  solverBadge: {
    fontFamily: 'var(--font-mono)', fontSize: 8, padding: '1px 6px', borderRadius: 100,
    background: 'rgba(26,122,63,0.10)', color: '#1A7A3F', border: '1px solid rgba(26,122,63,0.25)',
    letterSpacing: '0.05em', marginLeft: 4,
  },
  kpiRow:    { display: 'flex', gap: 16 },
  refreshBtn: {
    padding: 5, borderRadius: 7, border: '1px solid var(--border)',
    background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex',
  },
  updatedAt: { fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' },
  errText:   { color: 'var(--red)', fontSize: 11, fontFamily: 'var(--font-mono)', marginBottom: 8 },
};
