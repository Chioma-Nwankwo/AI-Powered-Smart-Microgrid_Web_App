import { useState, useEffect } from 'react';
import { Zap } from 'lucide-react';

export const APPLIANCE_CATALOG = {
  residential: [
    { id: 'ac',        label: 'Air Conditioner',   watts: 1500, hours: 8,   icon: '❄️' },
    { id: 'fridge',    label: 'Refrigerator',       watts: 150,  hours: 24,  icon: '🧊' },
    { id: 'tv',        label: 'Television',          watts: 120,  hours: 5,   icon: '📺' },
    { id: 'computer',  label: 'Desktop PC',          watts: 200,  hours: 8,   icon: '🖥️' },
    { id: 'laptop',    label: 'Laptop',              watts: 65,   hours: 6,   icon: '💻' },
    { id: 'fan',       label: 'Ceiling Fan',         watts: 75,   hours: 10,  icon: '🌀' },
    { id: 'lights',    label: 'LED Lights (×10)',    watts: 100,  hours: 6,   icon: '💡' },
    { id: 'microwave', label: 'Microwave',           watts: 1000, hours: 0.5, icon: '🍲' },
    { id: 'pump',      label: 'Water Pump',          watts: 750,  hours: 2,   icon: '💧' },
    { id: 'washing',   label: 'Washing Machine',     watts: 500,  hours: 1,   icon: '🧺' },
  ],
  commercial: [
    { id: 'ac_large',  label: 'Central A/C Unit',   watts: 5000, hours: 10,  icon: '❄️' },
    { id: 'computers', label: 'Workstations (×5)',   watts: 1000, hours: 9,   icon: '🖥️' },
    { id: 'lights',    label: 'Office Lights (×20)', watts: 400,  hours: 10,  icon: '💡' },
    { id: 'printers',  label: 'Laser Printer',       watts: 400,  hours: 4,   icon: '🖨️' },
    { id: 'server',    label: 'Server / Network',    watts: 500,  hours: 24,  icon: '🗄️' },
  ],
  industrial: [
    { id: 'machines',    label: 'Production Machinery', watts: 10000, hours: 8,  icon: '⚙️' },
    { id: 'hvac',        label: 'Industrial HVAC',       watts: 8000,  hours: 10, icon: '🌬️' },
    { id: 'lighting',    label: 'Industrial Lighting',   watts: 2000,  hours: 10, icon: '💡' },
    { id: 'compressor',  label: 'Air Compressor',        watts: 3000,  hours: 6,  icon: '🔧' },
  ],
  school: [
    { id: 'classrooms', label: 'Classroom Lights+Fan (×10)', watts: 1000, hours: 8, icon: '🏫' },
    { id: 'ac_class',   label: 'Classroom A/C (×5)',         watts: 7500, hours: 6, icon: '❄️' },
    { id: 'computers',  label: 'Computer Lab (×20)',         watts: 4000, hours: 5, icon: '🖥️' },
  ],
  hospital: [
    { id: 'hvac',     label: 'Central HVAC',       watts: 20000, hours: 24, icon: '❄️' },
    { id: 'medical',  label: 'Medical Equipment',  watts: 10000, hours: 12, icon: '🏥' },
    { id: 'lighting', label: 'Facility Lighting',  watts: 5000,  hours: 24, icon: '💡' },
    { id: 'kitchen',  label: 'Kitchen Equipment',  watts: 3000,  hours: 8,  icon: '🍳' },
  ],
};

// Rate per kWh in NGN — used for monthly estimate display
const RATE_NGN = 68;

function calcTotals(items) {
  const peak_kw   = items.reduce((s, a) => s + (a.watts * a.qty) / 1000, 0);
  const daily_kwh = items.reduce((s, a) => s + (a.watts * a.qty * a.hours) / 1000, 0);
  return { peak_kw, daily_kwh, monthly_kwh: daily_kwh * 30 };
}

/**
 * ApplianceCalculator
 * Props:
 *   buildingType  — 'residential' | 'commercial' | 'industrial' | 'school' | 'hospital'
 *   value         — [{ id, qty }]  (saved appliance qtys)
 *   onChange      — (appliances:[{id,qty}], peak_kw, daily_kwh) => void
 */
export default function ApplianceCalculator({ buildingType = 'residential', value = [], onChange }) {
  const catalog = APPLIANCE_CATALOG[buildingType] ?? APPLIANCE_CATALOG.residential;

  // Build qty map from saved value or default to 0
  const initQtys = () => {
    const saved = Object.fromEntries((value || []).map(a => [a.id, a.qty]));
    return Object.fromEntries(catalog.map(a => [a.id, saved[a.id] ?? 0]));
  };

  const [qtys, setQtys] = useState(initQtys);

  // Re-init when buildingType or value changes
  useEffect(() => { setQtys(initQtys()); }, [buildingType]);

  const items = catalog.map(a => ({ ...a, qty: qtys[a.id] ?? 0 }));
  const { peak_kw, daily_kwh, monthly_kwh } = calcTotals(items);

  const adjust = (id, delta) => {
    setQtys(prev => {
      const next = { ...prev, [id]: Math.max(0, (prev[id] ?? 0) + delta) };
      const nextItems = catalog.map(a => ({ ...a, qty: next[a.id] ?? 0 }));
      const totals    = calcTotals(nextItems);
      onChange?.(
        nextItems.filter(a => a.qty > 0).map(a => ({ id: a.id, qty: a.qty })),
        totals.peak_kw,
        totals.daily_kwh,
      );
      return next;
    });
  };

  const intensity = peak_kw < 3 ? 'low' : peak_kw < 10 ? 'med' : 'high';
  const barColor  = { low: '#10B981', med: '#F59E0B', high: '#F43F5E' }[intensity];

  return (
    <div style={s.wrap}>
      <div style={s.grid}>
        {catalog.map(a => {
          const qty = qtys[a.id] ?? 0;
          return (
            <div key={a.id} style={{ ...s.card, ...(qty > 0 ? s.cardActive : {}) }}>
              <span style={s.icon}>{a.icon}</span>
              <div style={s.info}>
                <span style={s.label}>{a.label}</span>
                <span style={s.sub}>{a.watts >= 1000 ? `${a.watts / 1000} kW` : `${a.watts} W`} · {a.hours}h/day</span>
              </div>
              <div style={s.stepper}>
                <button style={s.stepBtn} onClick={() => adjust(a.id, -1)} disabled={qty === 0}>−</button>
                <span style={s.qty}>{qty}</span>
                <button style={s.stepBtn} onClick={() => adjust(a.id, +1)}>+</button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Live totals bar */}
      <div style={s.summary}>
        <Zap size={13} color={barColor} />
        <span style={{ color: barColor, fontWeight: 600 }}>
          Peak {peak_kw.toFixed(1)} kW
        </span>
        <span style={s.dot}>·</span>
        <span style={s.sumText}>Daily {daily_kwh.toFixed(1)} kWh</span>
        <span style={s.dot}>·</span>
        <span style={s.sumText}>
          ~₦{Math.round(monthly_kwh * RATE_NGN).toLocaleString()}/month
        </span>
      </div>
    </div>
  );
}

const s = {
  wrap: { display: 'flex', flexDirection: 'column', gap: 12 },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
    gap: 8,
  },
  card: {
    display: 'flex', alignItems: 'center', gap: 10,
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 10, padding: '8px 10px',
    transition: 'border-color 0.15s',
  },
  cardActive: { border: '1px solid rgba(245,158,11,0.35)', background: 'rgba(245,158,11,0.05)' },
  icon:  { fontSize: 20, minWidth: 24, textAlign: 'center' },
  info:  { flex: 1, display: 'flex', flexDirection: 'column', gap: 1 },
  label: { fontSize: 12, color: 'var(--text-primary)', fontWeight: 500 },
  sub:   { fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' },
  stepper: { display: 'flex', alignItems: 'center', gap: 6 },
  stepBtn: {
    width: 24, height: 24, border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 6, background: 'transparent', color: 'var(--text-primary)',
    cursor: 'pointer', fontSize: 14, display: 'flex', alignItems: 'center',
    justifyContent: 'center', transition: 'background 0.1s',
  },
  qty: { minWidth: 18, textAlign: 'center', fontSize: 13, fontFamily: 'var(--font-mono)', color: 'var(--brown)' },
  summary: {
    display: 'flex', alignItems: 'center', gap: 8,
    background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 8, padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: 11,
  },
  dot:     { color: 'var(--text-muted)' },
  sumText: { color: 'var(--text-secondary)' },
};
