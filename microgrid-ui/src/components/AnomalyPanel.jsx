import { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, AlertCircle, XCircle, ShieldAlert } from 'lucide-react';
import { getAnomalies } from '../services/api';
import { formatDistanceToNow } from 'date-fns';
import { useLanguage } from '../context/LanguageContext';

const SEVERITY = {
  critical: { icon: XCircle,       color: '#B03A2E', bg: 'rgba(176,58,46,0.08)',  label: 'CRITICAL' },
  high:     { icon: AlertTriangle, color: '#C8793F', bg: 'rgba(200,121,63,0.10)', label: 'HIGH'     },
  medium:   { icon: AlertCircle,   color: '#D4860A', bg: 'rgba(212,134,10,0.08)', label: 'MEDIUM'   },
  low:      { icon: CheckCircle,   color: '#1A7A3F', bg: 'rgba(26,122,63,0.08)', label: 'LOW'      },
};

export default function AnomalyPanel({ country }) {
  const { t } = useLanguage();
  const [anomalies, setAnomalies] = useState([]);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    getAnomalies(country, 48)
      .then(({ data: res }) => {
        setAnomalies(res.anomalies ?? res.data ?? res ?? []);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [country]);

  const critCount = anomalies.filter(a => a.severity === 'critical' || a.severity === 'high').length;

  return (
    <div style={s.card} className="fade-up fade-up-4">
      {/* Header */}
      <div style={s.header}>
        <div style={s.titleRow}>
          <ShieldAlert size={15} color={critCount > 0 ? 'var(--red)' : 'var(--green)'} />
          <span style={s.title}>{t('anomalyDetection')}</span>
          <span style={s.subtitle}>— IF · PCA · OCSVM · AE ensemble</span>
        </div>
        <span style={{
          ...s.badge,
          background: critCount > 0 ? 'var(--red-dim)' : 'var(--green-dim)',
          color:      critCount > 0 ? 'var(--red)' : 'var(--green)',
        }}>
          {anomalies.length} event{anomalies.length !== 1 ? 's' : ''}
        </span>
      </div>

      {error && <p style={s.errText}>Failed to load — is Flask running?</p>}

      <div style={s.list}>
        {!loading && anomalies.length === 0 && !error && (
          <div style={s.empty}>
            <CheckCircle size={26} color="#1A7A3F" />
            <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 8, fontFamily: 'var(--font-mono)' }}>
              {t('noAnomalies')}
            </p>
          </div>
        )}

        {anomalies.map((item, i) => {
          const sev  = SEVERITY[item.severity ?? 'low'];
          const Icon = sev.icon;
          const ts   = item.timestamp ? new Date(item.timestamp) : null;
          return (
            <div key={i} style={{ ...s.item, borderLeft: `3px solid ${sev.color}` }}>
              <div style={{ ...s.iconWrap, background: sev.bg }}>
                <Icon size={13} color={sev.color} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
                  <p style={s.itemTitle}>{item.variable ?? 'Unknown variable'}</p>
                  <span style={{ ...s.sevBadge, color: sev.color, background: sev.bg }}>{sev.label}</span>
                </div>
                <p style={s.itemDesc}>
                  Score: <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                    {item.anomaly_score?.toFixed(3) ?? '—'}
                  </span>
                  {' · '}
                  Value: <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                    {item.value?.toFixed(2) ?? '—'}
                  </span>
                  {item.bounds && (
                    <span style={{ color: 'var(--text-muted)' }}>
                      {' '}[{item.bounds.lower?.toFixed(1)}, {item.bounds.upper?.toFixed(1)}]
                    </span>
                  )}
                </p>
                {item.detector_votes && (
                  <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                    {Object.entries(item.detector_votes).map(([det, flagged]) => (
                      <span key={det} style={{
                        fontSize: 8, fontFamily: 'var(--font-mono)', padding: '1px 5px',
                        borderRadius: 100, letterSpacing: '0.05em',
                        background: flagged ? 'var(--red-dim)' : 'var(--green-dim)',
                        color: flagged ? 'var(--red)' : 'var(--green)',
                        border: `1px solid ${flagged ? 'rgba(255,77,109,0.20)' : 'rgba(0,224,150,0.20)'}`,
                      }}>
                        {det === 'isolation_forest' ? 'IF' : det === 'pca_reconstruction' ? 'PCA' : det === 'autoencoder' ? 'AE' : 'OCSVM'}
                        {flagged ? ' ✕' : ' ✓'}
                      </span>
                    ))}
                  </div>
                )}
                {ts && (
                  <p style={s.itemTime}>{formatDistanceToNow(ts, { addSuffix: true })}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const s = {
  card: {
    background: 'var(--bg-card)', border: '1px solid var(--border)',
    borderRadius: 14, padding: '16px 18px', boxShadow: 'var(--shadow-card)',
    display: 'flex', flexDirection: 'column',
  },
  header:   { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  titleRow: { display: 'flex', alignItems: 'center', gap: 7 },
  title:    { fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.09em', fontWeight: 600 },
  subtitle: { fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' },
  badge:    { padding: '3px 10px', borderRadius: 100, fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 500 },
  list:     { display: 'flex', flexDirection: 'column', gap: 7, overflowY: 'auto', maxHeight: 280 },
  empty:    { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '28px 0' },
  item: {
    display: 'flex', gap: 10, padding: '9px 11px',
    background: 'var(--bg-elevated)', borderRadius: 9, alignItems: 'flex-start',
  },
  iconWrap: { width: 28, height: 28, borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  itemTitle: { fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' },
  itemDesc:  { fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 },
  itemTime:  { fontSize: 10, color: 'var(--text-muted)', marginTop: 2, fontFamily: 'var(--font-mono)' },
  sevBadge:  { fontSize: 9, fontFamily: 'var(--font-mono)', padding: '2px 7px', borderRadius: 100, letterSpacing: '0.06em', whiteSpace: 'nowrap' },
  errText:   { color: 'var(--red)', fontSize: 11, fontFamily: 'var(--font-mono)', marginBottom: 8 },
};
