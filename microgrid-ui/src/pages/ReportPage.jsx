import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { getForecast, getOptimization, getAnomalies, COUNTRIES } from '../services/api';
import { APPLIANCE_CATALOG, CURRENCY } from '../components/ApplianceCalculator';
import { useLanguage } from '../context/LanguageContext';
import { Printer, ArrowLeft } from 'lucide-react';

const BUILDING_CAPACITY = {
  residential: { battery_kwh: 15,  panel_kw: 8   },
  commercial:  { battery_kwh: 100, panel_kw: 50  },
  industrial:  { battery_kwh: 500, panel_kw: 200 },
  school:      { battery_kwh: 50,  panel_kw: 30  },
  hospital:    { battery_kwh: 200, panel_kw: 100 },
};

// Summarise forecast rows into stats for a given key prefix
function forecastStats(rows, prefix) {
  const vals = rows.map(r => r[`${prefix}_xgb`] ?? r[`${prefix}_rf`] ?? r[`${prefix}_gb`]).filter(v => v != null);
  if (!vals.length) return null;
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
  return { avg: avg.toFixed(1), max: Math.max(...vals).toFixed(1), min: Math.min(...vals).toFixed(1) };
}

export default function ReportPage({ selectedCountry, onCountryChange }) {
  const navigate  = useNavigate();
  const { t }     = useLanguage();
  const printRef  = useRef();
  const profile   = (() => { try { return JSON.parse(localStorage.getItem('gridai_user') || '{}'); } catch { return {}; } })();
  const country     = (profile.country || 'nigeria').toLowerCase();
  const btype       = profile.building_type || 'residential';
  const countryMeta = COUNTRIES[country] ?? COUNTRIES.nigeria;
  const curr        = CURRENCY[country] ?? CURRENCY.nigeria;

  const [forecast,     setForecast]     = useState(null);
  const [optimization, setOptimization] = useState(null);
  const [anomalies,    setAnomalies]    = useState(null);
  const [loading,      setLoading]      = useState(true);

  const caps = (profile.peak_demand_kw && profile.daily_kwh)
    ? {
        battery_kwh: Math.max(5,  Math.ceil(profile.daily_kwh      * 0.5)),
        panel_kw:    Math.max(2,  Math.ceil(profile.peak_demand_kw  * 1.2)),
      }
    : BUILDING_CAPACITY[btype] ?? BUILDING_CAPACITY.residential;

  useEffect(() => {
    Promise.all([
      getForecast(country, 48),
      getOptimization(country, caps.battery_kwh, caps.panel_kw),
      getAnomalies(country, 48),
    ]).then(([f, o, a]) => {
      setForecast(f.data);
      setOptimization(o.data);
      setAnomalies(a.data);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [country]);

  const handlePrint = () => window.print();

  const reportDate = new Date().toLocaleString('en-GB', {
    day: '2-digit', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });

  const forecastRows  = forecast?.forecast ?? [];
  const solar         = forecastStats(forecastRows, 'solar');
  const wind          = forecastStats(forecastRows, 'wind');
  const demandVals    = forecastRows.map(r => r.demand).filter(Boolean);
  const avgDemand     = demandVals.length ? (demandVals.reduce((a, b) => a + b, 0) / demandVals.length).toFixed(1) : '—';
  const anomalyCount  = anomalies?.anomalies?.length ?? 0;

  const catalog     = APPLIANCE_CATALOG[btype] ?? APPLIANCE_CATALOG.residential;
  const savedMap    = Object.fromEntries((profile.appliances || []).map(a => [a.id, a]));
  const activeAppliances = catalog.filter(a => (savedMap[a.id]?.qty ?? 0) > 0)
    .map(a => ({ ...a, qty: savedMap[a.id].qty, hours: savedMap[a.id].hours ?? a.hours, brand: savedMap[a.id].brand || '' }));

  const optSummary = optimization?.schedule ?? optimization?.summary ?? null;
  const solarGen    = optimization?.total_solar_generation ?? optimization?.solar_generated ?? null;
  const gridImport  = optimization?.total_grid_import      ?? optimization?.grid_import      ?? null;
  const costSaving  = optimization?.cost_savings            ?? optimization?.savings           ?? null;

  return (
    <div style={s.shell}>
      {/* Print-specific global styles injected inline */}
      <style>{`
        @media print {
          @page { size: A4; margin: 15mm 12mm; }
          .no-print { display: none !important; }
          .print-area { box-shadow: none !important; border: none !important; padding: 0 !important; margin: 0 !important; }
          body { background: #fff !important; color: #000 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .report-card { break-inside: avoid; page-break-inside: avoid; border: 1px solid #ddd !important; background: #fafafa !important; margin-bottom: 12px !important; }
          .report-stat-row { break-inside: avoid; page-break-inside: avoid; }
          .report-table { break-inside: avoid; page-break-inside: avoid; }
          .report-val   { color: #1a1a2e !important; }
          .report-label { color: #555 !important; }
          .report-title { color: #1a1a2e !important; page-break-after: avoid; }
          .report-meta  { color: #555 !important; }
          table { width: 100%; border-collapse: collapse; font-size: 10px; }
          th, td { padding: 4px 8px; border: 1px solid #ddd; }
        }
      `}</style>

      <div className="no-print">
        <Sidebar selectedCountry={selectedCountry} onCountryChange={onCountryChange} />
      </div>

      <main style={s.main}>
        {/* Toolbar — hidden on print */}
        <div style={s.toolbar} className="no-print">
          <button style={s.backBtn} onClick={() => navigate('/')}>
            <ArrowLeft size={14} /> {t('backToDashboard')}
          </button>
          <button style={s.printBtn} onClick={handlePrint} disabled={loading}>
            <Printer size={14} /> {loading ? t('loadingData') : t('printSavePdf')}
          </button>
        </div>

        {/* ── Report document ── */}
        <div style={s.doc} ref={printRef} className="print-area">

          {/* Header */}
          <div style={s.docHeader}>
            <div style={s.docLogo}>
              <span style={s.docLogoText}>GRID<span style={{ color: '#F59E0B' }}>AI</span></span>
              <span style={s.docLogoSub}>Smart Microgrid Analytics</span>
            </div>
            <div style={s.docMeta}>
              <p className="report-meta" style={s.metaLine}>{t('microgridReport')}</p>
              <p className="report-meta" style={s.metaDate}>Generated: {reportDate}</p>
            </div>
          </div>
          <div style={s.rule} />

          {/* Section 1: Facility Overview */}
          <Section title="1. Facility Overview">
            <div style={s.twoCol}>
              <MetaRow label="Account Name"    value={profile.name  || '—'} />
              <MetaRow label="Email"           value={profile.email || '—'} />
              <MetaRow label="Country"         value={`${countryMeta.flag} ${countryMeta.label}`} />
              <MetaRow label="Region / State"  value={profile.state || '—'} />
              <MetaRow label="Building Type"   value={btype.charAt(0).toUpperCase() + btype.slice(1)} />
              <MetaRow label="Address"         value={profile.address && profile.address !== 'Not specified' ? profile.address : '—'} />
            </div>
          </Section>

          {/* Section 2: Energy Consumption Profile */}
          {profile.peak_demand_kw > 0 && (
            <Section title="2. Energy Consumption Profile">
              <div style={s.statRow} className="report-stat-row">
                <StatBox label="Peak Demand"   value={`${profile.peak_demand_kw.toFixed(1)} kW`} />
                <StatBox label="Daily Usage"   value={`${(profile.daily_kwh || 0).toFixed(1)} kWh`} />
                <StatBox label="Monthly Usage" value={`${((profile.daily_kwh || 0) * 30).toFixed(0)} kWh`} />
                <StatBox label="Est. Monthly Bill" value={`${curr.symbol}${curr.rate >= 1 ? Math.round((profile.daily_kwh || 0) * 30 * curr.rate).toLocaleString() : ((profile.daily_kwh || 0) * 30 * curr.rate).toFixed(2)}`} />
              </div>
              {activeAppliances.length > 0 && (
                <div style={{ marginTop: 14 }}>
                  <p style={s.tableLabel}>Appliance Inventory</p>
                  <table style={s.table}>
                    <thead>
                      <tr>
                        {['Appliance', 'Brand', 'Rating', 'Qty', 'Daily Use', 'Daily kWh'].map(h => (
                          <th key={h} style={s.th}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {activeAppliances.map(a => (
                        <tr key={a.id}>
                          <td style={s.td}>{a.icon} {a.label}</td>
                          <td style={s.td}>{a.brand || '—'}</td>
                          <td style={s.td}>{a.watts >= 1000 ? `${a.watts/1000} kW` : `${a.watts} W`}</td>
                          <td style={s.td}>{a.qty}</td>
                          <td style={s.td}>{a.hours}h</td>
                          <td style={s.td}>{(a.watts * a.qty * a.hours / 1000).toFixed(2)} kWh</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Section>
          )}

          {/* Section 3: 48-Hour Forecast Summary */}
          <Section title={`${profile.peak_demand_kw > 0 ? '3' : '2'}. 48-Hour Forecast Summary`}>
            {loading
              ? <p style={s.loading}>Fetching forecast data…</p>
              : solar
              ? (
                <>
                  <div style={s.statRow} className="report-stat-row">
                    <StatBox label="Avg Solar Irradiance" value={`${solar.avg} W/m²`}    sub={`Peak ${solar.max} W/m²`} />
                    <StatBox label="Avg Wind Speed"       value={`${wind?.avg ?? '—'} m/s`} sub={wind ? `Peak ${wind.max} m/s` : ''} />
                    <StatBox label="Avg Grid Demand"      value={`${avgDemand} MW`}       sub="Country-level estimate" />
                    <StatBox label="Forecast Period"      value="48 hours"                sub={`${forecastRows.length} hourly points`} />
                  </div>
                  <p style={s.noteText}>
                    Solar and wind forecasts use an ensemble of Random Forest, Gradient Boosting, and XGBoost
                    models trained on ERA5 reanalysis data. Values shown are XGBoost model output
                    {forecast?.using_synthetic ? ' (physics-based clearsky estimate — ML models not deployed)' : ''}.
                  </p>
                </>
              )
              : <p style={s.loading}>Forecast data unavailable.</p>
            }
          </Section>

          {/* Section 4: Battery & Solar Optimisation */}
          <Section title={`${profile.peak_demand_kw > 0 ? '4' : '3'}. Battery & Solar Optimisation`}>
            {loading
              ? <p style={s.loading}>Fetching optimisation data…</p>
              : (
                <>
                  <div style={s.statRow} className="report-stat-row">
                    <StatBox label="Battery Capacity"  value={`${caps.battery_kwh} kWh`}
                             sub={profile.peak_demand_kw ? 'Based on your load' : 'Building-type default'} />
                    <StatBox label="Solar Array"       value={`${caps.panel_kw} kW`}
                             sub={profile.peak_demand_kw ? 'Based on your load' : 'Building-type default'} />
                    {solarGen  != null && <StatBox label="Solar Generated"  value={`${Number(solarGen).toFixed(1)} kWh`}  sub="Over 24h" />}
                    {gridImport != null && <StatBox label="Grid Import"     value={`${Number(gridImport).toFixed(1)} kWh`} sub="Over 24h" />}
                    {costSaving != null && <StatBox label="Cost Saving" value={`${curr.symbol}${curr.rate >= 1 ? Math.round(Number(costSaving)).toLocaleString() : Number(costSaving).toFixed(2)}`} sub="Over 24h" />}
                  </div>
                  <p style={s.noteText}>
                    Optimisation uses a Linear Programming (LP) model with battery SOC constraints,
                    solar generation forecast, and dynamic electricity tariff rates for {countryMeta.label}.
                  </p>
                </>
              )
            }
          </Section>

          {/* Section 5: Anomaly Detection */}
          <Section title={`${profile.peak_demand_kw > 0 ? '5' : '4'}. Anomaly Detection Status`}>
            {loading
              ? <p style={s.loading}>Fetching anomaly data…</p>
              : (
                <>
                  <div style={s.statRow} className="report-stat-row">
                    <StatBox
                      label="Anomalies (48h)"
                      value={String(anomalyCount)}
                      color={anomalyCount === 0 ? '#10B981' : anomalyCount < 3 ? '#F59E0B' : '#F43F5E'}
                      sub={anomalyCount === 0 ? 'No issues detected' : `${anomalyCount} event${anomalyCount > 1 ? 's' : ''} flagged`}
                    />
                    <StatBox label="Detection Method" value="Ensemble" sub="Isolation Forest + Z-score + IQR" />
                    <StatBox label="Monitoring Window" value="48 hours" sub="Hourly resolution" />
                  </div>
                  <p style={s.noteText}>
                    Anomaly detection uses an ensemble of three methods (Isolation Forest, Z-score, and IQR)
                    applied to solar irradiance, wind speed, and demand time series for {countryMeta.label}.
                  </p>
                </>
              )
            }
          </Section>

          {/* Footer */}
          <div style={s.docFooter}>
            <div style={s.rule} />
            <div style={s.footerRow}>
              <span style={s.footerLeft}>GridAI — AI-Powered Smart Microgrid Analytics System</span>
              <span style={s.footerRight}>Confidential · {new Date().getFullYear()}</span>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={sec.wrap} className="report-card">
      <h2 className="report-title" style={sec.title}>{title}</h2>
      {children}
    </div>
  );
}

function MetaRow({ label, value }) {
  return (
    <div style={mr.row}>
      <span className="report-label" style={mr.label}>{label}</span>
      <span className="report-val"   style={mr.value}>{value}</span>
    </div>
  );
}

function StatBox({ label, value, sub, color }) {
  return (
    <div style={sb.box}>
      <span className="report-val" style={{ ...sb.val, ...(color ? { color } : {}) }}>{value}</span>
      <span className="report-label" style={sb.label}>{label}</span>
      {sub && <span style={sb.sub}>{sub}</span>}
    </div>
  );
}

// ── Styles ──────────────────────────────────────────────────────────────────

const s = {
  shell:   { display: 'flex', minHeight: '100vh', background: 'var(--bg-base)' },
  main:    { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'auto', padding: '0 0 60px' },
  toolbar: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '12px 32px', borderBottom: '1px solid rgba(245,158,11,0.08)',
    background: 'rgba(15,15,20,0.85)', backdropFilter: 'blur(12px)',
    position: 'sticky', top: 0, zIndex: 10,
  },
  backBtn: {
    display: 'flex', alignItems: 'center', gap: 6,
    background: 'transparent', border: '1px solid rgba(255,255,255,0.1)',
    color: 'var(--text-secondary)', borderRadius: 7, padding: '6px 14px',
    cursor: 'pointer', fontSize: 12,
  },
  printBtn: {
    display: 'flex', alignItems: 'center', gap: 6,
    background: 'var(--brown)', border: 'none',
    color: '#040E1C', borderRadius: 7, padding: '7px 18px',
    cursor: 'pointer', fontSize: 12, fontWeight: 700,
  },
  doc: {
    maxWidth: 820, margin: '32px auto', padding: '40px 48px',
    background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 16, boxShadow: '0 4px 40px rgba(0,0,0,0.35)',
  },
  docHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 },
  docLogo:   { display: 'flex', flexDirection: 'column', gap: 2 },
  docLogoText: {
    fontFamily: 'Rajdhani, var(--font-display)', fontSize: 28, fontWeight: 700,
    letterSpacing: '0.12em', color: 'var(--text-primary)',
  },
  docLogoSub: { fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.08em' },
  docMeta:   { textAlign: 'right' },
  metaLine:  { fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 4px' },
  metaDate:  { fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', margin: 0 },
  rule:      { height: 1, background: 'rgba(245,158,11,0.15)', margin: '0 0 28px' },
  twoCol:    { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 24px' },
  statRow:   { display: 'flex', flexWrap: 'wrap', gap: 12, margin: '4px 0 8px' },
  noteText:  { fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.6, marginTop: 10 },
  loading:   { fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' },
  tableLabel: { fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12 },
  th: {
    textAlign: 'left', padding: '6px 10px',
    borderBottom: '1px solid rgba(255,255,255,0.1)',
    color: 'var(--text-muted)', fontWeight: 600,
    fontFamily: 'var(--font-mono)', fontSize: 10, textTransform: 'uppercase',
  },
  td: { padding: '6px 10px', borderBottom: '1px solid rgba(255,255,255,0.05)', color: 'var(--text-secondary)', fontSize: 12 },
  docFooter: { marginTop: 32 },
  footerRow: { display: 'flex', justifyContent: 'space-between', padding: '8px 0 0' },
  footerLeft:  { fontSize: 10, color: 'var(--text-muted)' },
  footerRight: { fontSize: 10, color: 'var(--text-muted)' },
};

const sec = {
  wrap:  { marginBottom: 28, padding: '18px 20px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.02)' },
  title: { fontSize: 13, fontWeight: 700, color: 'var(--brown)', marginBottom: 14, fontFamily: 'var(--font-display)', letterSpacing: '0.04em' },
};

const mr = {
  row:   { display: 'flex', gap: 8, padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)', alignItems: 'baseline' },
  label: { fontSize: 11, color: 'var(--text-muted)', minWidth: 130, flexShrink: 0 },
  value: { fontSize: 12, color: 'var(--text-primary)', fontWeight: 500 },
};

const sb = {
  box:   { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '10px 16px', minWidth: 120 },
  val:   { display: 'block', fontSize: 20, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' },
  label: { display: 'block', fontSize: 10, color: 'var(--text-muted)', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.05em' },
  sub:   { display: 'block', fontSize: 10, color: 'var(--text-muted)', marginTop: 2 },
};
