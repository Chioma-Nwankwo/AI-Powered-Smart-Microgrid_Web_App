import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import AppleLogin from 'react-apple-login';
import { useAuth } from '../context/AuthContext';
import useIsMobile from '../hooks/useIsMobile';
import GridBackground from '../components/GridBackground';

const GoogleIcon = () => (
  <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
    <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
    <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
    <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
    <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
  </svg>
);

const MicrosoftIcon = () => (
  <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
    <rect x="0"   y="0"   width="8.5" height="8.5" fill="#F25022"/>
    <rect x="9.5" y="0"   width="8.5" height="8.5" fill="#7FBA00"/>
    <rect x="0"   y="9.5" width="8.5" height="8.5" fill="#00A4EF"/>
    <rect x="9.5" y="9.5" width="8.5" height="8.5" fill="#FFB900"/>
  </svg>
);

const AppleIcon = () => (
  <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
    <path d="M15.07 9.6c-.02-1.96 1.6-2.9 1.67-2.95-0.91-1.33-2.33-1.51-2.84-1.53-1.21-.12-2.36.71-2.97.71-.62 0-1.57-.69-2.58-.67-1.33.02-2.56.77-3.24 1.96-1.38 2.39-.35 5.93 1 7.88.66.96 1.45 2.04 2.48 2 .99-.04 1.37-.64 2.57-.64 1.2 0 1.54.64 2.58.62 1.07-.02 1.75-0.98 2.4-1.94.76-1.11 1.07-2.19 1.09-2.24-.02-.01-2.12-.82-2.14-3.2z" fill="currentColor"/>
    <path d="M12.46 3.9c.55-.67.92-1.6.82-2.53-.79.03-1.75.53-2.32 1.19-.51.59-.95 1.54-.83 2.44.88.07 1.78-.45 2.33-1.1z" fill="currentColor"/>
  </svg>
);

// Animated electric grid logo
const GridIcon = () => (
  <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
    <path d="M14 3L4 9v10l10 6 10-6V9L14 3z" stroke="#F59E0B" strokeWidth="1.5" fill="none" opacity="0.9"/>
    <path d="M14 3v22M4 9l10 5 10-5" stroke="#F59E0B" strokeWidth="1" opacity="0.4"/>
    <circle cx="14" cy="14" r="2.5" fill="#FF9500" opacity="0.9"/>
  </svg>
);

// Feature list items shown on the left panel
const FEATURES = [
  { icon: '⚡', text: 'Real-time energy flow monitoring' },
  { icon: '🌤', text: '48-hour ML forecast (RF · GB · XGBoost)' },
  { icon: '🔋', text: 'LP battery optimization' },
  { icon: '🛡', text: 'Ensemble anomaly detection' },
  { icon: '🌍', text: 'Multi-country microgrid support' },
];

export default function Login() {
  const { signInWithGoogle, signInWithMicrosoft, signInWithApple, loginWithEmail, registerWithEmail, serverReady } = useAuth();
  const navigate  = useNavigate();
  const isMobile  = useIsMobile();
  const [loading,          setLoading]          = useState(null);
  const [error,            setError]            = useState('');
  const [email,            setEmail]            = useState('');
  const [password,         setPassword]         = useState('');
  const [confirmPassword,  setConfirmPassword]  = useState('');
  const [showEmailForm,    setShowEmailForm]    = useState(false);
  const [isSignUp,         setIsSignUp]         = useState(false);

  const handleMicrosoft = async () => {
    setLoading('microsoft');
    setError('');
    const result = await signInWithMicrosoft();
    setLoading(null);
    if (result.success) navigate(result.isNewUser ? '/onboarding' : '/');
    else setError(result.error || 'Microsoft sign-in failed. Check your Azure AD configuration.');
  };

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    if (isSignUp) {
      if (password !== confirmPassword) { setError('Passwords do not match.'); return; }
      if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
      setLoading('email');
      setError('');
      try {
        await registerWithEmail(email, password);
        navigate('/onboarding');
      } catch (err) {
        if (!err.response) {
          setError('Cannot reach server. Check your internet connection and try again.');
        } else {
          setError(err.response.data?.error || 'Registration failed. Please try again.');
        }
      } finally {
        setLoading(null);
      }
    } else {
      setLoading('email');
      setError('');
      try {
        await loginWithEmail(email, password);
        navigate('/');
      } catch (err) {
        setError(err?.response?.data?.error || 'Incorrect email or password.');
      } finally {
        setLoading(null);
      }
    }
  };

  return (
    <div style={s.page}>
      <GridBackground />

      {/* Left panel — hidden on mobile */}
      <div style={{ ...s.leftPanel, display: isMobile ? 'none' : 'flex' }}>
        <div style={s.leftInner}>
          <div style={s.brand}>
            <div style={s.brandIcon}><GridIcon /></div>
            <div>
              <span style={s.brandName}>GRID<span style={{ color: 'var(--accent)' }}>AI</span></span>
              <p style={s.brandSub}>Smart Microgrid Analytics</p>
            </div>
          </div>

          <div style={{ marginTop: 48 }}>
            <h2 style={s.leftTitle}>Connect your grid.<br />Understand your energy.</h2>
            <p style={s.leftDesc}>
              AI-powered analytics for microgrids. Monitor, forecast, optimize,
              and detect anomalies across your energy infrastructure in real time.
            </p>
          </div>

          <div style={s.featureList}>
            {FEATURES.map(f => (
              <div key={f.text} style={s.featureItem}>
                <span style={s.featureIcon}>{f.icon}</span>
                <span style={s.featureText}>{f.text}</span>
              </div>
            ))}
          </div>

          {/* Animated energy bar */}
          <div style={s.energyBar}>
            <div style={s.energyBarFill} />
          </div>
          <p style={s.energyLabel}>SYSTEM CAPACITY — 87.4%</p>
        </div>
      </div>

      {/* Right panel — auth form */}
      <div style={{ ...s.rightPanel, width: isMobile ? '100%' : 480, padding: isMobile ? 20 : 40 }}>
        <div style={{ ...s.card, padding: isMobile ? '28px 20px 22px' : '36px 36px 28px' }} className="fade-up">
          {!serverReady && (
            <div style={s.wakeupBanner}>
              <span style={s.wakeupDot} />
              Server is starting up, please wait a moment…
            </div>
          )}

          <div style={s.cardHeader}>
            <h1 style={s.title}>{isSignUp && showEmailForm ? 'Create account' : 'Sign in'}</h1>
            <p style={s.subtitle}>{isSignUp && showEmailForm ? 'Join GridAI — complete setup after sign-up' : 'Access your microgrid dashboard'}</p>
          </div>

          {/* OAuth buttons */}
          {!showEmailForm && (
            <div style={s.btnGroup}>
              <div style={{ width: '100%' }}>
                <GoogleLogin
                  onSuccess={async (credentialResponse) => {
                    setLoading('google');
                    setError('');
                    try {
                      const result = await signInWithGoogle(credentialResponse.credential);
                      navigate(result.isNewUser ? '/onboarding' : '/');
                    } catch (err) {
                      setError(err?.response?.data?.error || 'Google sign-in failed. Please try again.');
                    } finally {
                      setLoading(null);
                    }
                  }}
                  onError={() => { setError('Google sign-in was cancelled.'); setLoading(null); }}
                  width="100%"
                  text="continue_with"
                  shape="rectangular"
                  theme="outline"
                  size="large"
                />
              </div>

              <button
                style={{ ...s.oauthBtn, ...((loading === 'microsoft' || !serverReady) ? s.btnDisabled : {}) }}
                onClick={handleMicrosoft}
                disabled={!!loading || !serverReady}
              >
                <MicrosoftIcon />
                {loading === 'microsoft' ? 'Connecting…' : 'Continue with Microsoft'}
              </button>

              {import.meta.env.VITE_APPLE_CLIENT_ID && (
                <AppleLogin
                  clientId={import.meta.env.VITE_APPLE_CLIENT_ID}
                  redirectURI={import.meta.env.VITE_APP_URL || window.location.origin}
                  usePopup={true}
                  scope="name email"
                  responseMode="form_post"
                  callback={async (res) => {
                    if (res?.error) { setError('Apple sign-in was cancelled.'); return; }
                    setLoading('apple');
                    setError('');
                    try {
                      const result = await signInWithApple(
                        res.authorization.id_token,
                        res.user ?? null
                      );
                      navigate(result.isNewUser ? '/onboarding' : '/');
                    } catch {
                      setError('Apple sign-in failed. Please try again.');
                    } finally {
                      setLoading(null);
                    }
                  }}
                  render={({ onClick }) => (
                    <button
                      style={{ ...s.oauthBtn, ...(loading === 'apple' ? s.btnDisabled : {}) }}
                      onClick={onClick}
                      disabled={!!loading}
                    >
                      <AppleIcon />
                      {loading === 'apple' ? 'Connecting…' : 'Continue with Apple'}
                    </button>
                  )}
                />
              )}

              <div style={s.divider}>
                <span style={s.divLine} />
                <span style={s.divText}>or</span>
                <span style={s.divLine} />
              </div>

              <button style={s.emailToggle} onClick={() => setShowEmailForm(true)}>
                Sign in with email
              </button>
            </div>
          )}

          {/* Email / password form */}
          {showEmailForm && (
            <form onSubmit={handleEmailSubmit} style={s.form}>
              <div style={s.inputWrap}>
                <label style={s.label}>Email address</label>
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  style={s.input}
                  autoFocus
                  required
                />
              </div>
              <div style={s.inputWrap}>
                <label style={s.label}>Password</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  style={s.input}
                  required
                />
              </div>
              {isSignUp && (
                <div style={s.inputWrap}>
                  <label style={s.label}>Confirm password</label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    style={s.input}
                    required
                  />
                </div>
              )}
              <button
                type="submit"
                style={{ ...s.submitBtn, ...((loading === 'email' || !serverReady) ? s.btnDisabled : {}) }}
                disabled={!!loading || !serverReady}
              >
                {loading === 'email'
                  ? (isSignUp ? 'Creating account…' : 'Authenticating…')
                  : (isSignUp ? 'Create account →' : 'Sign in →')
                }
              </button>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <button type="button" style={s.backLink} onClick={() => { setShowEmailForm(false); setIsSignUp(false); setError(''); }}>
                  ← Back
                </button>
                <button type="button" style={s.toggleLink} onClick={() => { setIsSignUp(v => !v); setError(''); setConfirmPassword(''); }}>
                  {isSignUp ? 'Already have an account?' : "Don't have an account?"}
                </button>
              </div>
            </form>
          )}

          {error && (
            <div style={s.errorBox}>
              <span>⚠</span> {error}
            </div>
          )}

          <p style={s.footer}>
            ERA5 reanalysis data · ML forecasting · LP optimization
          </p>
        </div>
      </div>
    </div>
  );
}

const s = {
  page: {
    minHeight: '100vh', display: 'flex', position: 'relative',
    background: 'var(--bg-base)', overflow: 'hidden',
  },

  /* ── Left panel */
  leftPanel: {
    flex: 1, display: 'flex', alignItems: 'center',
    padding: '48px 60px', position: 'relative', zIndex: 5,
    borderRight: '1px solid rgba(245,158,11,0.08)',
  },
  leftInner: { maxWidth: 480 },
  brand: { display: 'flex', alignItems: 'center', gap: 12 },
  brandIcon: {
    width: 52, height: 52,
    background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.22)',
    borderRadius: 14, display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 0 20px rgba(245,158,11,0.15)',
  },
  brandName: {
    fontFamily: 'var(--font-display)', fontSize: 26, fontWeight: 700,
    letterSpacing: '0.12em', color: 'var(--text-primary)',
  },
  brandSub: { fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 3 },
  leftTitle: {
    fontFamily: 'var(--font-display)', fontSize: 34, fontWeight: 700,
    color: 'var(--text-primary)', letterSpacing: '0.03em', lineHeight: 1.2, marginBottom: 16,
  },
  leftDesc: { fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.7 },
  featureList: { marginTop: 32, display: 'flex', flexDirection: 'column', gap: 14 },
  featureItem: { display: 'flex', alignItems: 'center', gap: 12 },
  featureIcon: { fontSize: 18, width: 28, flexShrink: 0 },
  featureText: { fontSize: 13, color: 'var(--text-secondary)' },

  energyBar: {
    marginTop: 40, height: 3, background: 'rgba(245,158,11,0.10)',
    borderRadius: 100, overflow: 'hidden',
  },
  energyBarFill: {
    height: '100%', width: '87.4%',
    background: 'linear-gradient(90deg, rgba(245,158,11,0.6) 0%, #F59E0B 100%)',
    borderRadius: 100,
    boxShadow: '0 0 8px rgba(245,158,11,0.5)',
    animation: 'pulse 2s ease-in-out infinite',
  },
  energyLabel: {
    fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--primary)',
    letterSpacing: '0.14em', marginTop: 8, opacity: 0.7,
  },

  /* ── Right panel */
  rightPanel: {
    width: 480, display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: 40, position: 'relative', zIndex: 5,
  },
  card: {
    background: 'rgba(7,21,37,0.85)', backdropFilter: 'blur(20px)',
    border: '1px solid rgba(245,158,11,0.12)', borderRadius: 20,
    padding: '36px 36px 28px', width: '100%',
    boxShadow: '0 0 0 1px rgba(245,158,11,0.04), 0 20px 60px rgba(0,0,0,0.60)',
  },
  cardHeader: { marginBottom: 28 },
  title: {
    fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 700,
    color: 'var(--text-primary)', letterSpacing: '0.04em', marginBottom: 6,
  },
  subtitle: { fontSize: 13, color: 'var(--text-muted)' },

  btnGroup: { display: 'flex', flexDirection: 'column', gap: 10 },
  oauthBtn: {
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
    padding: '11px 20px', borderRadius: 10,
    border: '1px solid rgba(245,158,11,0.14)',
    background: 'rgba(245,158,11,0.05)', color: 'var(--text-primary)',
    fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: 500, cursor: 'pointer',
    transition: 'all 0.18s ease',
  },
  divider: { display: 'flex', alignItems: 'center', gap: 12, margin: '4px 0' },
  divLine: { flex: 1, height: 1, background: 'rgba(245,158,11,0.08)' },
  divText: { fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.06em', fontFamily: 'var(--font-mono)' },
  emailToggle: {
    padding: '11px 20px', borderRadius: 10,
    border: '1px solid rgba(245,158,11,0.10)',
    background: 'transparent', color: 'var(--text-secondary)',
    fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: 500, cursor: 'pointer',
    transition: 'all 0.18s',
  },

  form: { display: 'flex', flexDirection: 'column', gap: 14 },
  inputWrap: { display: 'flex', flexDirection: 'column', gap: 6 },
  label: { fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' },
  input: {
    padding: '11px 14px', borderRadius: 10,
    border: '1px solid rgba(245,158,11,0.12)',
    background: 'rgba(245,158,11,0.04)', color: 'var(--text-primary)',
    fontFamily: 'var(--font-body)', fontSize: 14, outline: 'none',
    transition: 'all 0.15s',
  },
  submitBtn: {
    padding: '13px 20px', borderRadius: 10, border: 'none',
    background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
    color: '#000', fontFamily: 'var(--font-body)', fontSize: 14,
    fontWeight: 700, cursor: 'pointer', marginTop: 4,
    boxShadow: '0 0 20px rgba(245,158,11,0.30)',
    transition: 'all 0.18s',
    letterSpacing: '0.04em',
  },
  backLink: {
    background: 'none', border: 'none', color: 'var(--text-muted)',
    fontFamily: 'var(--font-body)', fontSize: 12, cursor: 'pointer',
    textAlign: 'left', padding: '4px 0',
  },
  toggleLink: {
    background: 'none', border: 'none', color: 'var(--primary)',
    fontFamily: 'var(--font-body)', fontSize: 12, cursor: 'pointer',
    textAlign: 'right', padding: '4px 0', opacity: 0.85,
  },
  btnDisabled: { opacity: 0.50, cursor: 'not-allowed' },
  wakeupBanner: {
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '8px 12px', borderRadius: 8, marginBottom: 16,
    background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.18)',
    fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)',
    letterSpacing: '0.04em',
  },
  wakeupDot: {
    width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
    background: '#F59E0B', animation: 'pulse 1.2s ease-in-out infinite',
  },
  errorBox: {
    marginTop: 14, padding: '10px 14px', borderRadius: 8,
    background: 'rgba(255,77,109,0.08)', border: '1px solid rgba(255,77,109,0.20)',
    color: 'var(--red)', fontSize: 12, fontFamily: 'var(--font-mono)',
    display: 'flex', alignItems: 'flex-start', gap: 8,
  },
  footer: {
    marginTop: 24, textAlign: 'center', fontSize: 9,
    color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em',
  },
};
