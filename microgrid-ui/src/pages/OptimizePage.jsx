import React from 'react';
import Sidebar           from '../components/Sidebar';
import OptimizationChart from '../components/OptimizationChart';
import GridBackground    from '../components/GridBackground';
import { COUNTRIES }      from '../services/api';
import { useLanguage }    from '../context/LanguageContext';
import { Zap, Battery, Sun, DollarSign } from 'lucide-react';

const BUILDING_CAPACITY = {
  residential: { battery_kwh: 15,  panel_kw: 8   },
  commercial:  { battery_kwh: 100, panel_kw: 50  },
  industrial:  { battery_kwh: 500, panel_kw: 200 },
  school:      { battery_kwh: 50,  panel_kw: 30  },
  hospital:    { battery_kwh: 200, panel_kw: 100 },
};

export default function OptimizePage({ selectedCountry, onCountryChange }) {
  const { t } = useLanguage();
  const { label, flag } = COUNTRIES[selectedCountry];
  const profile = (() => { try { return JSON.parse(localStorage.getItem('gridai_user') || '{}'); } catch { return {}; } })();
  const btype   = profile.building_type?.toLowerCase() || 'commercial';
  // Use user's measured load if they've completed appliance setup; fall back to building-type defaults
  const caps = (profile.peak_demand_kw && profile.daily_kwh)
    ? {
        battery_kwh: Math.max(5,  Math.ceil(profile.daily_kwh      * 0.5)),
        panel_kw:    Math.max(2,  Math.ceil(profile.peak_demand_kw  * 1.2)),
      }
    : BUILDING_CAPACITY[btype] ?? BUILDING_CAPACITY.commercial;

  return (
    <div style={s.shell}>
      <GridBackground />
      <Sidebar selectedCountry={selectedCountry} onCountryChange={onCountryChange} />

      <main style={s.main}>
        <header style={s.topBar}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <Zap size={18} color="var(--caramel, var(--brown))" />
            <div>
              <h1 style={s.pageTitle}>
                {flag} {label}
                <span style={s.pageSub}> — {t('batteryOptimization')}</span>
              </h1>
              <p style={s.pageDesc}>LP/MILP dispatch · 24-hour schedule · {btype} · {caps.battery_kwh} kWh / {caps.panel_kw} kW</p>
            </div>
          </div>
          <div style={s.topRight}>
            <div className="pulse-dot" />
            <span style={s.liveLabel}>{t('live')}</span>
          </div>
        </header>

        <div style={s.content}>
          {/* Optimization chart */}
          <OptimizationChart country={selectedCountry} />

          {/* Strategy explanation */}
          <div style={s.strategyRow}>
            {[
              {
                icon: Sun,     color: '#C8793F',
                title: 'Solar Surplus Charging',
                desc:  'When solar generation exceeds load, excess energy charges the battery up to 95 % SoC at max C/4 rate.',
              },
              {
                icon: Battery, color: '#7B52A8',
                title: 'Peak-Hour Discharge',
                desc:  'Battery discharges when solar cannot cover load, maintaining minimum 10 % SoC reserve at all times.',
              },
              {
                icon: DollarSign, color: '#1A7A3F',
                title: 'Time-of-Use Pricing',
                desc:  'Grid import cost is weighted 1.5× during 18:00–21:00 peak and 0.8× during off-peak hours 23:00–06:00.',
              },
            ].map(({ icon: Icon, color, title, desc }) => (
              <div key={title} style={{ ...s.stratCard, borderTop: `3px solid ${color}` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <div style={{ ...s.stratIcon, background: `${color}18` }}>
                    <Icon size={14} color={color} />
                  </div>
                  <span style={s.stratTitle}>{title}</span>
                </div>
                <p style={s.stratDesc}>{desc}</p>
              </div>
            ))}
          </div>

          {/* Parameter reference */}
          <div style={s.paramCard}>
            <p style={s.paramTitle}>Default System Parameters</p>
            <div style={s.paramGrid}>
              {[
                { label: 'Battery capacity',  value: `${caps.battery_kwh} kWh` },
                { label: 'Solar panel peak',  value: `${caps.panel_kw} kW`     },
                { label: 'Charge efficiency', value: '95 %'                     },
                { label: 'Max charge rate',   value: 'C / 4'                    },
                { label: 'Min SoC',           value: '10 %'                     },
                { label: 'Max SoC',           value: '95 %'                     },
              ].map(p => (
                <div key={p.label} style={s.paramItem}>
                  <span style={s.paramLabel}>{p.label}</span>
                  <span style={s.paramValue}>{p.value}</span>
                </div>
              ))}
            </div>
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

  strategyRow: { display: 'flex', gap: 12 },
  stratCard: {
    flex: 1, background: 'var(--bg-card)', border: '1px solid var(--border)',
    borderRadius: 12, padding: '14px 16px', boxShadow: 'var(--shadow-card)',
  },
  stratIcon:  { width: 28, height: 28, borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  stratTitle: { fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' },
  stratDesc:  { fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.6 },

  paramCard: {
    background: 'var(--bg-card)', border: '1px solid var(--border)',
    borderRadius: 12, padding: '14px 18px', boxShadow: 'var(--shadow-card)',
  },
  paramTitle: { fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.10em', textTransform: 'uppercase', marginBottom: 12 },
  paramGrid:  { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px 20px' },
  paramItem:  { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid var(--border)' },
  paramLabel: { fontSize: 11, color: 'var(--text-secondary)' },
  paramValue: { fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-primary)', fontWeight: 600 },
};
