import { useState, useEffect } from 'react';
import { Zap } from 'lucide-react';

export const APPLIANCE_CATALOG = {
  residential: [
    { id: 'ac',        label: 'Air Conditioner',  watts: 1500, hours: 8,   icon: '❄️' },
    { id: 'fridge',    label: 'Refrigerator',      watts: 150,  hours: 24,  icon: '🧊' },
    { id: 'tv',        label: 'Television',         watts: 120,  hours: 5,   icon: '📺' },
    { id: 'computer',  label: 'Desktop PC',         watts: 200,  hours: 8,   icon: '🖥️' },
    { id: 'laptop',    label: 'Laptop',             watts: 65,   hours: 6,   icon: '💻' },
    { id: 'fan',       label: 'Ceiling Fan',        watts: 75,   hours: 10,  icon: '🌀' },
    { id: 'lights',    label: 'LED Lights',         watts: 100,  hours: 6,   icon: '💡' },
    { id: 'microwave', label: 'Microwave',          watts: 1000, hours: 0.5, icon: '🍲' },
    { id: 'pump',      label: 'Water Pump',         watts: 750,  hours: 2,   icon: '💧' },
    { id: 'washing',   label: 'Washing Machine',    watts: 500,  hours: 1,   icon: '🧺' },
  ],
  commercial: [
    { id: 'ac_large',  label: 'Central A/C Unit',  watts: 5000, hours: 10,  icon: '❄️' },
    { id: 'computers', label: 'Workstation',        watts: 200,  hours: 9,   icon: '🖥️' },
    { id: 'lights',    label: 'Office Light Zone',  watts: 400,  hours: 10,  icon: '💡' },
    { id: 'printers',  label: 'Laser Printer',      watts: 400,  hours: 4,   icon: '🖨️' },
    { id: 'server',    label: 'Server / Network',   watts: 500,  hours: 24,  icon: '🗄️' },
  ],
  industrial: [
    { id: 'machines',   label: 'Production Machine', watts: 10000, hours: 8,  icon: '⚙️' },
    { id: 'hvac',       label: 'Industrial HVAC',     watts: 8000,  hours: 10, icon: '🌬️' },
    { id: 'lighting',   label: 'Industrial Lighting', watts: 2000,  hours: 10, icon: '💡' },
    { id: 'compressor', label: 'Air Compressor',      watts: 3000,  hours: 6,  icon: '🔧' },
  ],
  school: [
    { id: 'classrooms', label: 'Classroom (Lights+Fan)', watts: 100,  hours: 8, icon: '🏫' },
    { id: 'ac_class',   label: 'Classroom A/C',          watts: 1500, hours: 6, icon: '❄️' },
    { id: 'computers',  label: 'Computer Workstation',   watts: 200,  hours: 5, icon: '🖥️' },
  ],
  hospital: [
    { id: 'hvac',     label: 'Central HVAC',      watts: 20000, hours: 24, icon: '❄️' },
    { id: 'medical',  label: 'Medical Equipment', watts: 10000, hours: 12, icon: '🏥' },
    { id: 'lighting', label: 'Facility Lighting', watts: 5000,  hours: 24, icon: '💡' },
    { id: 'kitchen',  label: 'Kitchen Equipment', watts: 3000,  hours: 8,  icon: '🍳' },
  ],
};

export const CURRENCY = {
  nigeria:   { symbol: '₦',  rate: 68   },
  australia: { symbol: 'A$', rate: 0.28 },
  germany:   { symbol: '€',  rate: 0.30 },
  canada:    { symbol: 'C$', rate: 0.13 },
};

function calcTotals(items) {
  const peak_kw   = items.reduce((s, a) => s + (a.watts * a.qty) / 1000, 0);
  const daily_kwh = items.reduce((s, a) => s + (a.watts * a.qty * a.hours) / 1000, 0);
  return { peak_kw, daily_kwh, monthly_kwh: daily_kwh * 30 };
}

/**
 * ApplianceCalculator
 * Props:
 *   buildingType — 'residential' | 'commercial' | 'industrial' | 'school' | 'hospital'
 *   value        — [{ id, qty, hours?, brand? }]
 *   onChange     — (appliances, peak_kw, daily_kwh) => void
 *   country      — 'nigeria' | 'australia' | 'germany' | 'canada'
 */
export default function ApplianceCalculator({ buildingType = 'residential', value = [], onChange, country = 'nigeria' }) {
  const catalog = APPLIANCE_CATALOG[buildingType] ?? APPLIANCE_CATALOG.residential;
  const curr    = CURRENCY[(country || 'nigeria').toLowerCase()] ?? CURRENCY.nigeria;

  const initQtys = () => {
    const saved = Object.fromEntries((value || []).map(a => [a.id, a.qty]));
    return Object.fromEntries(catalog.map(a => [a.id, saved[a.id] ?? 0]));
  };
  const initHours = () => {
    const saved = Object.fromEntries((value || []).filter(a => a.hours != null).map(a => [a.id, a.hours]));
    return Object.fromEntries(catalog.map(a => [a.id, saved[a.id] ?? a.hours]));
  };
  const initBrands = () =>
    Object.fromEntries((value || []).filter(a => a.brand).map(a => [a.id, a.brand]));

  const [qtys,   setQtys]   = useState(initQtys);
  const [hours,  setHours]  = useState(initHours);
  const [brands, setBrands] = useState(initBrands);

  useEffect(() => {
    setQtys(initQtys());
    setHours(initHours());
    setBrands(initBrands());
  }, [buildingType]);

  const fire = (nq, nh, nb) => {
    const nextItems = catalog.map(a => ({ ...a, qty: nq[a.id] ?? 0, hours: nh[a.id] ?? a.hours }));
    const totals    = calcTotals(nextItems);
    onChange?.(
      nextItems.filter(a => a.qty > 0).map(a => ({
        id: a.id, qty: a.qty, hours: a.hours, brand: nb[a.id] || '',
      })),
      totals.peak_kw,
      totals.daily_kwh,
    );
  };

  const setQty = (id, val) => {
    const next = { ...qtys, [id]: Math.max(0, val) };
    setQtys(next);
    fire(next, hours, brands);
  };
  const setHrs = (id, val) => {
    const next = { ...hours, [id]: Math.min(24, Math.max(0, parseFloat(val) || 0)) };
    setHours(next);
    fire(qtys, next, brands);
  };
  const setBrand = (id, val) => {
    const next = { ...brands, [id]: val };
    setBrands(next);
    fire(qtys, hours, next);
  };

  const items = catalog.map(a => ({ ...a, qty: qtys[a.id] ?? 0, hours: hours[a.id] ?? a.hours }));
  const { peak_kw, daily_kwh, monthly_kwh } = calcTotals(items);

  const intensity = peak_kw < 3 ? 'low' : peak_kw < 10 ? 'med' : 'high';
  const barColor  = { low: '#10B981', med: '#F59E0B', high: '#F43F5E' }[intensity];

  return (
    <div style={s.wrap}>
      <div style={s.grid}>
        {catalog.map(a => {
          const qty = qtys[a.id] ?? 0;
          const hrs = hours[a.id] ?? a.hours;
          return (
            <div key={a.id} style={s.cardWrap}>
              <div style={{ ...s.card, ...(qty > 0 ? s.cardActive : {}) }}>
                <span style={s.icon}>{a.icon}</span>
                <div style={s.info}>
                  <span style={s.label}>{a.label}</span>
                  <span style={s.sub}>{a.watts >= 1000 ? `${a.watts / 1000} kW` : `${a.watts} W`}</span>
                </div>
                <div style={s.controls}>
                  <div style={s.inputRow}>
                    <span style={s.inputLbl}>Qty</span>
                    <div style={s.stepper}>
                      <button style={s.stepBtn} onClick={() => setQty(a.id, qty - 1)} disabled={qty === 0}>−</button>
                      <input
                        type="number" min={0} value={qty}
                        onChange={e => setQty(a.id, parseInt(e.target.value) || 0)}
                        style={s.numInput}
                      />
                      <button style={s.stepBtn} onClick={() => setQty(a.id, qty + 1)}>+</button>
                    </div>
                  </div>
                  <div style={s.inputRow}>
                    <span style={s.inputLbl}>h/day</span>
                    <input
                      type="number" min={0} max={24} step={0.5} value={hrs}
                      onChange={e => setHrs(a.id, e.target.value)}
                      style={{ ...s.numInput, width: 44 }}
                    />
                  </div>
                </div>
              </div>
              {qty > 0 && (
                <input
                  type="text"
                  placeholder="Brand (optional, e.g. LG, Samsung)"
                  value={brands[a.id] || ''}
                  onChange={e => setBrand(a.id, e.target.value)}
                  style={s.brandInput}
                />
              )}
            </div>
          );
        })}
      </div>

      <div style={s.summary}>
        <Zap size={13} color={barColor} />
        <span style={{ color: barColor, fontWeight: 600 }}>Peak {peak_kw.toFixed(1)} kW</span>
        <span style={s.dot}>·</span>
        <span style={s.sumText}>Daily {daily_kwh.toFixed(1)} kWh</span>
        <span style={s.dot}>·</span>
        <span style={s.sumText}>
          ~{curr.symbol}{(monthly_kwh * curr.rate).toLocaleString(undefined, { maximumFractionDigits: curr.rate < 1 ? 2 : 0 })}/month
        </span>
      </div>
    </div>
  );
}

const s = {
  wrap: { display: 'flex', flexDirection: 'column', gap: 12 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 8 },

  cardWrap: { display: 'flex', flexDirection: 'column', gap: 4 },
  card: {
    display: 'flex', alignItems: 'center', gap: 10,
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 10, padding: '8px 10px', transition: 'border-color 0.15s',
  },
  cardActive: { border: '1px solid rgba(245,158,11,0.35)', background: 'rgba(245,158,11,0.05)' },
  icon:  { fontSize: 20, minWidth: 24, textAlign: 'center', flexShrink: 0 },
  info:  { flex: 1, display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 },
  label: { fontSize: 12, color: 'var(--text-primary)', fontWeight: 500 },
  sub:   { fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' },

  controls:  { display: 'flex', flexDirection: 'column', gap: 4, flexShrink: 0 },
  inputRow:  { display: 'flex', alignItems: 'center', gap: 4 },
  inputLbl:  { fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', minWidth: 26, textAlign: 'right' },
  stepper:   { display: 'flex', alignItems: 'center', gap: 3 },
  stepBtn: {
    width: 20, height: 20, border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 5, background: 'transparent', color: 'var(--text-primary)',
    cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center',
    justifyContent: 'center', transition: 'background 0.1s', flexShrink: 0,
  },
  numInput: {
    width: 36, height: 20, border: '1px solid rgba(245,158,11,0.25)',
    borderRadius: 5, background: 'transparent', color: 'var(--brown)',
    fontFamily: 'var(--font-mono)', fontSize: 11, textAlign: 'center',
    outline: 'none', padding: '0 2px',
  },
  brandInput: {
    width: '100%', padding: '5px 10px',
    border: '1px solid rgba(245,158,11,0.15)', borderRadius: 7,
    background: 'rgba(245,158,11,0.03)', color: 'var(--text-secondary)',
    fontFamily: 'var(--font-body)', fontSize: 11, outline: 'none',
  },

  summary: {
    display: 'flex', alignItems: 'center', gap: 8,
    background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 8, padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: 11,
  },
  dot:     { color: 'var(--text-muted)' },
  sumText: { color: 'var(--text-secondary)' },
};
