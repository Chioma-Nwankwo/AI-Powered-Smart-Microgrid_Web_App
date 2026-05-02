import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import GridBackground from '../components/GridBackground';
import { Zap, MapPin, Building2, ClipboardList, CheckCircle } from 'lucide-react';
import axios from 'axios';

const COUNTRIES_LIST = [
  { key: 'nigeria',   flag: '🇳🇬', label: 'Nigeria',   states: ['FCT', 'Lagos', 'Kano', 'Rivers', 'Oyo', 'Kaduna', 'Anambra', 'Enugu', 'Imo', 'Other'] },
  { key: 'australia', flag: '🇦🇺', label: 'Australia',  states: ['New South Wales', 'Victoria', 'Queensland', 'Western Australia', 'South Australia', 'Tasmania', 'Other'] },
  { key: 'germany',   flag: '🇩🇪', label: 'Germany',    states: ['Berlin', 'Bavaria', 'Hamburg', 'Hesse', 'Baden-Württemberg', 'North Rhine-Westphalia', 'Other'] },
  { key: 'canada',    flag: '🇨🇦', label: 'Canada',     states: ['Ontario', 'Quebec', 'British Columbia', 'Alberta', 'Manitoba', 'Saskatchewan', 'Other'] },
];

const BUILDING_TYPES = [
  { key: 'residential', label: 'Residential', icon: '🏠', desc: 'House, apartment, or flat' },
  { key: 'commercial',  label: 'Commercial',  icon: '🏢', desc: 'Office, shop, or business' },
  { key: 'industrial',  label: 'Industrial',  icon: '🏭', desc: 'Factory or warehouse' },
  { key: 'school',      label: 'School / University', icon: '🏫', desc: 'Educational institution' },
  { key: 'hospital',    label: 'Hospital / Clinic', icon: '🏥', desc: 'Healthcare facility' },
];

const BUILDING_FIELDS = {
  residential: [
    { id: 'house_number', label: 'House / Flat Number', placeholder: 'e.g. 14B' },
    { id: 'street',       label: 'Street Name',         placeholder: 'e.g. Ahmadu Bello Way' },
    { id: 'monthly_kwh',  label: 'Approx. Monthly Usage (kWh)', placeholder: 'e.g. 300', type: 'number' },
  ],
  commercial: [
    { id: 'business_name', label: 'Business Name',    placeholder: 'e.g. Bright Tech Ltd' },
    { id: 'street',        label: 'Address',           placeholder: 'e.g. 22 Victoria Island' },
    { id: 'floor_area',    label: 'Floor Area (m²)',    placeholder: 'e.g. 500', type: 'number' },
  ],
  industrial: [
    { id: 'facility_name', label: 'Facility Name',     placeholder: 'e.g. Delta Steel Plant' },
    { id: 'industry_type', label: 'Industry Type',     placeholder: 'e.g. Textile, Food Processing' },
    { id: 'peak_demand',   label: 'Peak Demand (kW)',  placeholder: 'e.g. 2000', type: 'number' },
  ],
  school: [
    { id: 'institution_name', label: 'Institution Name', placeholder: 'e.g. University of Lagos' },
    { id: 'num_buildings',    label: 'Number of Buildings', placeholder: 'e.g. 12', type: 'number' },
  ],
  hospital: [
    { id: 'facility_name', label: 'Facility Name',   placeholder: 'e.g. General Hospital Abuja' },
    { id: 'num_beds',      label: 'Number of Beds',  placeholder: 'e.g. 200', type: 'number' },
  ],
};

const STEPS = [
  { label: 'Location',      icon: MapPin },
  { label: 'Building type', icon: Building2 },
  { label: 'Details',       icon: ClipboardList },
];

// State/city-level coordinates for map navigation after onboarding
const STATE_COORDS = {
  nigeria: {
    'FCT':     [7.3986,   9.0765],
    'Lagos':   [3.3792,   6.5244],
    'Kano':    [8.5200,  12.0000],
    'Rivers':  [7.0134,   4.8156],
    'Oyo':     [3.9470,   7.3775],
    'Kaduna':  [7.4479,  10.5264],
    'Anambra': [6.7527,   6.2255],
    'Enugu':   [7.4952,   6.4584],
    'Imo':     [7.0490,   5.4920],
  },
  australia: {
    'New South Wales':    [151.2093, -33.8688],
    'Victoria':           [144.9631, -37.8136],
    'Queensland':         [153.0251, -27.4698],
    'Western Australia':  [115.8605, -31.9505],
    'South Australia':    [138.6007, -34.9285],
    'Tasmania':           [147.3272, -42.8821],
  },
  germany: {
    'Berlin':                   [13.4050,  52.5200],
    'Bavaria':                  [11.5820,  48.1351],
    'Hamburg':                  [ 9.9937,  53.5511],
    'Hesse':                    [ 8.6821,  50.1109],
    'Baden-Württemberg':        [ 9.1829,  48.7758],
    'North Rhine-Westphalia':   [ 6.7735,  51.2217],
  },
  canada: {
    'Ontario':          [-79.3832,  43.6532],
    'Quebec':           [-73.5673,  45.5017],
    'British Columbia': [-123.1207, 49.2827],
    'Alberta':          [-114.0719, 51.0447],
    'Manitoba':         [ -97.1384, 49.8951],
    'Saskatchewan':     [-104.6189, 50.4452],
  },
};

export default function Onboarding({ onComplete }) {
  const { user } = useAuth();
  const navigate  = useNavigate();
  const [step,    setStep]    = useState(0);
  const [country, setCountry] = useState('');
  const [state,   setState]   = useState('');
  const [btype,   setBtype]   = useState('');
  const [details, setDetails] = useState({});
  const [saving,     setSaving]     = useState(false);
  const [error,      setError]      = useState('');
  const [detecting,  setDetecting]  = useState(false);
  const [detected,   setDetected]   = useState(null); // { country, state, city, lat, lon }

  const selectedCountry = COUNTRIES_LIST.find(c => c.key === country);

  const handleDetectLocation = async () => {
    setDetecting(true);
    try {
      // Try browser GPS first for precision, fall back to IP geo
      const pos = await new Promise((res, rej) =>
        navigator.geolocation
          ? navigator.geolocation.getCurrentPosition(res, rej, { timeout: 5000 })
          : rej(new Error('no geo'))
      ).catch(() => null);

      const params = pos
        ? `lat=${pos.coords.latitude}&long=${pos.coords.longitude}`
        : '';
      const res = await axios.get(`/api/location/detect?${params}`);
      const d   = res.data;

      // Match detected country to one of our 4 supported countries
      const countryMap = { Nigeria: 'nigeria', Australia: 'australia', Germany: 'germany', Canada: 'canada' };
      const matched = countryMap[d.country] || null;

      setDetected({
        country: matched,
        state:   d.state   || '',
        city:    d.city    || '',
        lat:     d.latitude  || null,
        lon:     d.longitude || null,
      });
    } catch {
      setDetected({ country: null, state: '', city: '', lat: null, lon: null });
    } finally {
      setDetecting(false);
    }
  };

  const applyDetected = () => {
    if (!detected) return;
    if (detected.country) setCountry(detected.country);
    if (detected.state)   setState(detected.state);
    setDetected(null);
    // GPS detects coordinates only — advance to building type step so user
    // sees immediately that they need to pick it (cannot be auto-detected)
    if (detected.country && detected.state) setStep(1);
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const address = Object.entries(details)
        .filter(([, v]) => v)
        .map(([k, v]) => `${k}: ${v}`)
        .join(', ') || 'completed';

      const token = localStorage.getItem('jwt_token');
      await axios.put(
        '/api/user/profile',
        { country, state, building_type: btype, address },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Look up state-level coordinates for map navigation
      const coords = STATE_COORDS[country]?.[state] ?? null;
      const stored = JSON.parse(localStorage.getItem('gridai_user') || '{}');
      localStorage.setItem('gridai_user', JSON.stringify({
        ...stored, country, state, building_type: btype, address,
        userLng: coords ? coords[0] : stored.userLng,
        userLat: coords ? coords[1] : stored.userLat,
      }));

      onComplete(country);
    } catch (err) {
      setError('Could not save profile. Please try again.');
      setSaving(false);
    }
  };

  return (
    <div style={s.page}>
      <GridBackground />

      {/* Left panel — ambient context */}
      <div style={s.leftPanel}>
        <div style={s.brand}>
          <div style={s.brandIcon}>
            <Zap size={22} color="#F59E0B" />
          </div>
          <span style={s.brandText}>GRID<span style={{ color: '#F59E0B' }}>AI</span></span>
        </div>

        <div style={s.heroText}>
          <h1 style={s.heroTitle}>Connect your<br />microgrid.</h1>
          <p style={s.heroSub}>
            Tell us where your energy system is located and what kind of facility
            you're running. GridAI will calibrate its forecasts, anomaly thresholds,
            and dispatch strategy to your grid's specific context.
          </p>
        </div>

        <div style={s.featureList}>
          {[
            { icon: '📡', text: 'ERA5 climate data matched to your region' },
            { icon: '⚡', text: 'ML forecast tuned to local solar irradiance' },
            { icon: '🔋', text: 'Battery dispatch optimised for your load profile' },
            { icon: '🛡️', text: 'Anomaly detection calibrated to normal range' },
          ].map(({ icon, text }) => (
            <div key={text} style={s.featureItem}>
              <span style={s.featureIcon}>{icon}</span>
              <span style={s.featureText}>{text}</span>
            </div>
          ))}
        </div>

        {/* Signal animation */}
        <div style={s.signalBar}>
          <span style={s.signalLabel}>GRID SIGNAL</span>
          <div style={s.signalTrack}>
            <div style={{ ...s.signalFill, width: `${[33, 55, 80][step]}%` }} />
          </div>
          <span style={s.signalPct}>{[33, 55, 100][step]}%</span>
        </div>
      </div>

      {/* Right panel — wizard card */}
      <div style={s.rightPanel}>
        <div style={s.card}>
          {/* Progress stepper */}
          <div style={s.stepper}>
            {STEPS.map(({ label, icon: Icon }, i) => (
              <div key={i} style={s.stepperItem}>
                <div style={{
                  ...s.stepDot,
                  ...(step === i ? s.stepDotActive : step > i ? s.stepDotDone : {}),
                }}>
                  {step > i
                    ? <CheckCircle size={12} color="#040E1C" />
                    : <Icon size={12} color={step === i ? '#040E1C' : 'var(--text-muted)'} />
                  }
                </div>
                <span style={{
                  ...s.stepLabel,
                  ...(step >= i ? { color: step === i ? '#F59E0B' : 'var(--text-secondary)' } : {}),
                }}>
                  {label}
                </span>
                {i < STEPS.length - 1 && (
                  <div style={{ ...s.stepLine, ...(step > i ? s.stepLineActive : {}) }} />
                )}
              </div>
            ))}
          </div>

          {/* Step 0: Country + State */}
          {step === 0 && (
            <div>
              <h2 style={s.stepTitle}>Where is your microgrid located?</h2>
              <p style={s.stepDesc}>Select your country and region to calibrate ERA5 climate data.</p>

              {/* Auto-detect banner */}
              {detected ? (
                <div style={s.detectBanner}>
                  <span style={s.detectEmoji}>📍</span>
                  <div style={{ flex: 1 }}>
                    <p style={s.detectMain}>
                      {detected.country
                        ? `Detected: ${detected.city ? detected.city + ', ' : ''}${detected.state ? detected.state + ', ' : ''}${detected.country.charAt(0).toUpperCase() + detected.country.slice(1)}`
                        : 'Location detected but not in a supported country'}
                    </p>
                    {detected.country && (
                      <p style={s.detectSub}>
                        {detected.state
                          ? 'Location found — select your building type on the next step'
                          : 'Country found — please select your region below'}
                      </p>
                    )}
                  </div>
                  {detected.country && (
                    <button onClick={applyDetected} style={s.detectYes}>Use it</button>
                  )}
                  <button onClick={() => setDetected(null)} style={s.detectDismiss}>✕</button>
                </div>
              ) : (
                <>
                  <button onClick={handleDetectLocation} disabled={detecting} style={s.detectBtn}>
                    {detecting ? '⏳ Detecting…' : '📍 Detect my location'}
                  </button>
                  <p style={s.detectHint}>Detects your country & city · Building type must be selected manually</p>
                </>
              )}

              <div style={s.countryGrid}>
                {COUNTRIES_LIST.map(c => (
                  <button key={c.key} onClick={() => { setCountry(c.key); setState(''); }}
                    style={{ ...s.countryCard, ...(country === c.key ? s.countryCardActive : {}) }}>
                    <span style={s.countryFlag}>{c.flag}</span>
                    <span style={s.countryCardLabel}>{c.label}</span>
                    {country === c.key && (
                      <div style={s.countryCheck}><CheckCircle size={11} color="#F59E0B" /></div>
                    )}
                  </button>
                ))}
              </div>
              {selectedCountry && (
                <div style={{ marginTop: 16 }}>
                  <label style={s.label}>Region / State</label>
                  <select value={state} onChange={e => setState(e.target.value)} style={s.select}>
                    <option value="">Select region…</option>
                    {selectedCountry.states.map(st => (
                      <option key={st} value={st}>{st}</option>
                    ))}
                  </select>
                </div>
              )}
              <button
                onClick={() => setStep(1)}
                disabled={!country || !state}
                style={{ ...s.nextBtn, ...(!country || !state ? s.btnDisabled : {}) }}
              >
                Continue →
              </button>
            </div>
          )}

          {/* Step 1: Building type */}
          {step === 1 && (
            <div>
              <h2 style={s.stepTitle}>What type of building?</h2>
              <p style={s.stepDesc}>This tailors your energy forecast and anomaly thresholds.</p>
              <div style={s.btypeGrid}>
                {BUILDING_TYPES.map(b => (
                  <button key={b.key} onClick={() => setBtype(b.key)}
                    style={{ ...s.btypeCard, ...(btype === b.key ? s.btypeCardActive : {}) }}>
                    <span style={s.btypeIcon}>{b.icon}</span>
                    <div>
                      <span style={s.btypeLabel}>{b.label}</span>
                      <span style={s.btypeDesc}>{b.desc}</span>
                    </div>
                    {btype === b.key && (
                      <div style={{ marginLeft: 'auto' }}><CheckCircle size={13} color="#F59E0B" /></div>
                    )}
                  </button>
                ))}
              </div>
              <div style={s.navRow}>
                <button onClick={() => setStep(0)} style={s.backBtn}>← Back</button>
                <button onClick={() => setStep(2)} disabled={!btype}
                  style={{ ...s.nextBtn, ...(!btype ? s.btnDisabled : {}) }}>
                  Continue →
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Building details */}
          {step === 2 && (
            <div>
              <h2 style={s.stepTitle}>Building details</h2>
              <p style={s.stepDesc}>Fill in what you can — all fields are optional.</p>
              <div style={s.fieldsGrid}>
                {(BUILDING_FIELDS[btype] || []).map(f => (
                  <div key={f.id} style={s.field}>
                    <label style={s.label}>{f.label}</label>
                    <input
                      type={f.type || 'text'}
                      placeholder={f.placeholder}
                      value={details[f.id] || ''}
                      onChange={e => setDetails(prev => ({ ...prev, [f.id]: e.target.value }))}
                      style={s.input}
                    />
                  </div>
                ))}
              </div>
              {error && <p style={s.error}>{error}</p>}
              <div style={s.navRow}>
                <button onClick={() => setStep(1)} style={s.backBtn}>← Back</button>
                <button onClick={handleSave} disabled={saving}
                  style={{ ...s.nextBtn, ...(saving ? s.btnDisabled : {}) }}>
                  {saving ? 'Connecting…' : 'Connect to Grid →'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const s = {
  page: {
    minHeight: '100vh', display: 'flex', flexDirection: 'row',
    background: '#040E1C', position: 'relative', overflow: 'hidden',
  },

  /* Left panel */
  leftPanel: {
    width: 380, flexShrink: 0, padding: '48px 40px',
    display: 'flex', flexDirection: 'column', gap: 32,
    position: 'relative', zIndex: 2,
    borderRight: '1px solid rgba(245,158,11,0.10)',
  },
  brand: { display: 'flex', alignItems: 'center', gap: 10 },
  brandIcon: {
    width: 36, height: 36, borderRadius: 9,
    background: 'rgba(245,158,11,0.10)', border: '1px solid rgba(245,158,11,0.22)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 0 12px rgba(245,158,11,0.20)',
  },
  brandText: {
    fontFamily: 'Rajdhani, var(--font-display)', fontSize: 20, fontWeight: 700,
    letterSpacing: '0.12em', color: '#E5F4FF',
  },
  heroText: { flex: 1, display: 'flex', flexDirection: 'column', gap: 14 },
  heroTitle: {
    fontFamily: 'Rajdhani, var(--font-display)', fontSize: 36, fontWeight: 700,
    color: '#E5F4FF', lineHeight: 1.15, letterSpacing: '0.02em',
  },
  heroSub: { fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 },
  featureList: { display: 'flex', flexDirection: 'column', gap: 12 },
  featureItem: { display: 'flex', alignItems: 'center', gap: 12 },
  featureIcon: { fontSize: 16, flexShrink: 0 },
  featureText: { fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 },

  signalBar: { display: 'flex', alignItems: 'center', gap: 10 },
  signalLabel: {
    fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)',
    letterSpacing: '0.10em', whiteSpace: 'nowrap',
  },
  signalTrack: {
    flex: 1, height: 4, borderRadius: 100,
    background: 'rgba(245,158,11,0.10)', overflow: 'hidden',
  },
  signalFill: {
    height: '100%', borderRadius: 100,
    background: 'linear-gradient(90deg, #F59E0B 0%, #FF9500 100%)',
    boxShadow: '0 0 8px rgba(245,158,11,0.50)',
    transition: 'width 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
  },
  signalPct: { fontFamily: 'var(--font-mono)', fontSize: 10, color: '#F59E0B', fontWeight: 600 },

  /* Right panel */
  rightPanel: {
    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: '48px 32px', position: 'relative', zIndex: 2,
  },
  card: {
    background: 'rgba(7,21,37,0.85)', backdropFilter: 'blur(20px)',
    border: '1px solid rgba(245,158,11,0.12)',
    borderRadius: 20, padding: '36px 40px', width: '100%', maxWidth: 520,
    boxShadow: '0 0 60px rgba(0,0,0,0.60), 0 0 120px rgba(245,158,11,0.05)',
  },

  /* Stepper */
  stepper: { display: 'flex', alignItems: 'center', marginBottom: 28, gap: 0 },
  stepperItem: { display: 'flex', alignItems: 'center', gap: 7 },
  stepDot: {
    width: 26, height: 26, borderRadius: '50%',
    background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.18)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  stepDotActive: {
    background: '#F59E0B', border: '1px solid #F59E0B',
    boxShadow: '0 0 14px rgba(245,158,11,0.55)',
  },
  stepDotDone: {
    background: 'rgba(0,224,150,0.80)', border: '1px solid #00E096',
  },
  stepLabel: {
    fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)',
    whiteSpace: 'nowrap', letterSpacing: '0.04em',
  },
  stepLine: { width: 24, height: 2, background: 'rgba(245,158,11,0.10)', margin: '0 8px' },
  stepLineActive: { background: 'rgba(0,224,150,0.60)' },

  /* Step content */
  stepTitle: {
    fontFamily: 'Rajdhani, var(--font-display)', fontSize: 22, fontWeight: 700,
    color: 'var(--text-primary)', marginBottom: 6,
  },
  stepDesc: { fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 },

  /* Country grid */
  countryGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 },
  countryCard: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
    padding: '14px 10px', borderRadius: 12, position: 'relative',
    border: '1px solid rgba(245,158,11,0.10)',
    background: 'rgba(14,32,53,0.80)',
    cursor: 'pointer', transition: 'all 0.18s',
  },
  countryCardActive: {
    border: '1.5px solid rgba(245,158,11,0.55)',
    background: 'rgba(245,158,11,0.07)',
    boxShadow: '0 0 20px rgba(245,158,11,0.12)',
  },
  countryFlag: { fontSize: 28 },
  countryCardLabel: { fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' },
  countryCheck: { position: 'absolute', top: 8, right: 8 },

  /* Building type */
  btypeGrid: { display: 'flex', flexDirection: 'column', gap: 8 },
  btypeCard: {
    display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
    borderRadius: 10, border: '1px solid rgba(245,158,11,0.10)',
    background: 'rgba(14,32,53,0.80)', cursor: 'pointer', textAlign: 'left',
    transition: 'all 0.18s',
  },
  btypeCardActive: {
    border: '1.5px solid rgba(245,158,11,0.55)',
    background: 'rgba(245,158,11,0.07)',
    boxShadow: '0 0 16px rgba(245,158,11,0.10)',
  },
  btypeIcon: { fontSize: 22, flexShrink: 0 },
  btypeLabel: {
    display: 'block', fontWeight: 600, fontSize: 14,
    color: 'var(--text-primary)', marginBottom: 2,
  },
  btypeDesc: { display: 'block', fontSize: 11, color: 'var(--text-muted)' },

  /* Fields */
  fieldsGrid: { display: 'flex', flexDirection: 'column', gap: 14 },
  field: { display: 'flex', flexDirection: 'column', gap: 5 },
  label: {
    fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)',
    fontFamily: 'var(--font-mono)', letterSpacing: '0.04em',
  },
  select: {
    padding: '10px 12px', borderRadius: 9,
    border: '1px solid rgba(245,158,11,0.14)',
    background: 'rgba(14,32,53,0.90)',
    color: 'var(--text-primary)', fontFamily: 'var(--font-body)', fontSize: 14,
    width: '100%', marginTop: 6, outline: 'none',
  },
  input: {
    padding: '10px 12px', borderRadius: 9,
    border: '1px solid rgba(245,158,11,0.14)',
    background: 'rgba(14,32,53,0.90)',
    color: 'var(--text-primary)', fontFamily: 'var(--font-body)', fontSize: 14,
    outline: 'none', width: '100%', boxSizing: 'border-box',
  },

  /* Navigation */
  navRow: { display: 'flex', justifyContent: 'space-between', marginTop: 24, gap: 12 },
  backBtn: {
    padding: '10px 18px', borderRadius: 9,
    border: '1px solid rgba(245,158,11,0.18)',
    background: 'transparent', color: 'var(--text-secondary)',
    fontFamily: 'var(--font-body)', fontSize: 13, cursor: 'pointer',
  },
  nextBtn: {
    padding: '11px 24px', borderRadius: 9, border: 'none', marginTop: 20,
    background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
    color: '#040E1C', fontFamily: 'var(--font-body)', fontSize: 13, fontWeight: 700,
    cursor: 'pointer', width: '100%',
    boxShadow: '0 4px 20px rgba(245,158,11,0.30)',
    letterSpacing: '0.02em',
  },
  btnDisabled: { opacity: 0.35, cursor: 'not-allowed', boxShadow: 'none' },
  error: { color: 'var(--red)', fontSize: 12, marginTop: 8, fontFamily: 'var(--font-mono)' },

  detectBtn: {
    width: '100%', padding: '9px 16px', borderRadius: 9, marginBottom: 4,
    border: '1px solid rgba(245,158,11,0.28)', background: 'rgba(245,158,11,0.06)',
    color: '#F59E0B', fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600,
    cursor: 'pointer', letterSpacing: '0.06em',
  },
  detectHint: {
    fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em', textAlign: 'center', marginBottom: 14, opacity: 0.7,
  },
  detectBanner: {
    display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14,
    padding: '10px 14px', borderRadius: 9,
    background: 'rgba(16,185,129,0.07)', border: '1px solid rgba(16,185,129,0.22)',
  },
  detectEmoji: { fontSize: 18 },
  detectMain:  { fontSize: 12, color: '#FAFAF9', fontWeight: 600 },
  detectSub:   { fontSize: 10, color: '#10B981', fontFamily: 'var(--font-mono)', marginTop: 2 },
  detectYes:   {
    padding: '5px 12px', borderRadius: 7, border: 'none',
    background: 'rgba(16,185,129,0.20)', color: '#10B981',
    fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, cursor: 'pointer',
  },
  detectDismiss: {
    padding: '4px 8px', borderRadius: 6, border: 'none',
    background: 'transparent', color: 'var(--text-muted)', fontSize: 12, cursor: 'pointer',
  },
};
