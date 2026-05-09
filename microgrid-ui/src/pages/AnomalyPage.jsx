import Sidebar        from '../components/Sidebar';
import AnomalyPanel   from '../components/AnomalyPanel';
import GridBackground from '../components/GridBackground';
import { COUNTRIES }  from '../services/api';
import { useLanguage } from '../context/LanguageContext';
import { ShieldAlert, GitBranch, Layers, Activity } from 'lucide-react';

export default function AnomalyPage({ selectedCountry, onCountryChange }) {
  const { t } = useLanguage();
  const { label, flag } = COUNTRIES[selectedCountry];

  return (
    <div style={s.shell}>
      <GridBackground />
      <Sidebar selectedCountry={selectedCountry} onCountryChange={onCountryChange} />

      <main style={s.main}>
        <header style={s.topBar}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <ShieldAlert size={18} color="#B03A2E" />
            <div>
              <h1 style={s.pageTitle}>
                {flag} {label}
                <span style={s.pageSub}> — {t('anomalyDetection')}</span>
              </h1>
              <p style={s.pageDesc}>IF · PCA · OCSVM · AE ensemble · majority vote ≥ 2/4 · 48-hour window</p>
            </div>
          </div>
          <div style={s.topRight}>
            <div className="pulse-dot" />
            <span style={s.liveLabel}>{t('live')}</span>
          </div>
        </header>

        <div style={s.content}>
          {/* Anomaly list — expanded */}
          <AnomalyPanel country={selectedCountry} />

          {/* Ensemble methodology section */}
          <div style={s.ensembleCard}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
              <Layers size={15} color="var(--brown)" />
              <span style={s.ensembleTitle}>Ensemble Anomaly Detection — How It Works</span>
              <span style={s.activeNow}>ACTIVE</span>
            </div>
            <div style={s.ensembleGrid}>
              {[
                {
                  icon: GitBranch, color: '#2471A3', active: true,
                  name: 'Isolation Forest',
                  desc: 'Isolates anomalies by randomly partitioning the feature space. Points that require fewer splits are flagged — effective on high-dimensional energy time-series.',
                },
                {
                  icon: Layers, color: '#7B52A8', active: true,
                  name: 'PCA Reconstruction',
                  desc: 'Principal Component Analysis captures variance in normal operation. Residuals beyond 3σ of reconstruction error are classified as anomalies.',
                },
                {
                  icon: ShieldAlert, color: '#1A7A3F', active: true,
                  name: 'One-Class SVM',
                  desc: 'Learns a hypersphere boundary around normal operating data. Points outside the RBF kernel boundary are flagged as out-of-distribution anomalies.',
                },
                {
                  icon: Activity, color: '#64748B', active: true,
                  name: 'Autoencoder',
                  desc: 'MLP-based reconstruction network trained to reproduce normal operating patterns. High reconstruction error indicates anomalous behaviour in solar irradiance and demand profiles.',
                },
              ].map(({ icon: Icon, color, name, desc, active }) => (
                <div key={name} style={{ ...s.ensembleItem, borderLeft: `3px solid ${color}`, opacity: active ? 1 : 0.5 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 6 }}>
                    <Icon size={13} color={color} />
                    <span style={s.ensembleName}>{name}</span>
                    {!active && <span style={s.comingSoon}>planned</span>}
                  </div>
                  <p style={s.ensembleDesc}>{desc}</p>
                </div>
              ))}
            </div>
            <p style={s.ensembleNote}>
              Four detectors run simultaneously on the 48-hour forecast window. An event is flagged when ≥ 2 of the 4 models agree (majority vote).
              Severity is determined by the fraction of models voting positive and the magnitude of deviation from the learned normal range.
            </p>
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

  ensembleCard: {
    background: 'var(--bg-card)', border: '1px solid var(--border)',
    borderRadius: 14, padding: '16px 18px', boxShadow: 'var(--shadow-card)',
  },
  ensembleTitle: { fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', letterSpacing: '0.08em' },
  activeNow: {
    fontFamily: 'var(--font-mono)', fontSize: 9, padding: '2px 8px', borderRadius: 100,
    background: 'rgba(16,185,129,0.12)', color: 'var(--green)', border: '1px solid rgba(16,185,129,0.25)',
    letterSpacing: '0.06em', fontWeight: 600,
  },
  comingSoon: {
    fontFamily: 'var(--font-mono)', fontSize: 9, padding: '2px 8px', borderRadius: 100,
    background: 'rgba(100,116,139,0.12)', color: '#94A3B8', border: '1px solid rgba(100,116,139,0.2)',
    letterSpacing: '0.06em', fontWeight: 600,
  },
  ensembleGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 },
  ensembleItem: {
    background: 'var(--bg-elevated)', borderRadius: 9,
    padding: '10px 14px', border: '1px solid var(--border)',
  },
  ensembleName: { fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' },
  ensembleDesc: { fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.6 },
  ensembleNote: { fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', lineHeight: 1.7, borderTop: '1px solid var(--border)', paddingTop: 12 },
};
