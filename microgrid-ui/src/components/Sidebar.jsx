import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, TrendingUp, Zap, AlertTriangle, Settings, LogOut, Wifi, FileText } from 'lucide-react';
import { useAuth }     from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { COUNTRIES }   from '../services/api';
import { COUNTRY_LANGUAGES } from '../i18n/translations';

const GridIcon = () => (
  <svg width="18" height="18" viewBox="0 0 22 22" fill="none">
    <path d="M11 2L3 7v8l8 5 8-5V7L11 2z" stroke="#F59E0B" strokeWidth="1.8" fill="none"/>
    <path d="M11 2v18M3 7l8 4 8-4" stroke="#F59E0B" strokeWidth="1.1" opacity="0.5"/>
  </svg>
);

export default function Sidebar({ selectedCountry, onCountryChange }) {
  const { user, signOut }    = useAuth();
  const { lang, setLang, t } = useLanguage();
  const navigate             = useNavigate();

  const NAV = [
    { to: '/',         icon: LayoutDashboard, label: t('dashboard'),    color: '#F59E0B' },
    { to: '/forecast', icon: TrendingUp,      label: t('forecast'),     color: '#10B981' },
    { to: '/optimize', icon: Zap,             label: t('optimization'), color: '#FBBF24' },
    { to: '/anomaly',  icon: AlertTriangle,   label: t('anomaly'),      color: '#F43F5E' },
    { to: '/report',   icon: FileText,        label: t('report'),       color: '#38BDF8' },
    { to: '/settings', icon: Settings,        label: t('settings'),     color: '#A78BFA' },
  ];

  const availableLangs = COUNTRY_LANGUAGES[selectedCountry] ?? [{ code: 'en', name: 'English' }];

  return (
    <>
      {/* Desktop vertical sidebar */}
      <aside className="sidebar-panel" style={s.sidebar}>
        {/* Logo */}
        <div style={s.logo}>
          <div style={s.logoIcon}><GridIcon /></div>
          <div>
            <span style={s.logoText}>
              GRID<span style={{ color: '#10B981' }}>AI</span>
            </span>
            <p style={s.logoSub}>Microgrid Analytics</p>
          </div>
          <div style={s.connStatus}><div className="pulse-dot" /></div>
        </div>

        {/* Scrollable middle section */}
        <div style={s.scrollArea}>

        {/* Nav */}
        <nav style={s.nav}>
          {NAV.map(({ to, icon: Icon, label, color }) => (
            <NavLink key={to} to={to} end={to === '/'} style={({ isActive }) => ({
              ...s.navLink,
              ...(isActive ? { ...s.navActive, '--nav-color': color } : {}),
            })}>
              {({ isActive }) => (
                <>
                  <div style={{
                    ...s.navIconWrap,
                    background: isActive ? `${color}1A` : 'transparent',
                    border: `1px solid ${isActive ? `${color}40` : 'transparent'}`,
                  }}>
                    <Icon size={14} color={isActive ? color : 'var(--text-muted)'} />
                  </div>
                  <span style={{ color: isActive ? color : 'var(--text-muted)' }}>{label}</span>
                  {isActive && <div style={{ ...s.activeBar, background: color }} />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Grid connection */}
        <div style={s.connCard}>
          <Wifi size={11} color="var(--green)" />
          <div>
            <p style={s.connLabel}>GRID CONNECTED</p>
            <p style={s.connSub}>Live · {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
          </div>
        </div>

        {/* Country selector */}
        <div style={s.section}>
          <p style={s.sectionLabel}>{t('activeRegion')}</p>
          {Object.entries(COUNTRIES).map(([key, { label, flag }]) => {
            const active = selectedCountry === key;
            return (
              <button key={key} onClick={() => onCountryChange(key)}
                style={{ ...s.countryBtn, ...(active ? s.countryActive : {}) }}>
                <span style={s.flag}>{flag}</span>
                <span style={{ ...s.countryLabel, ...(active ? s.countryLabelActive : {}) }}>{label}</span>
                {active && <span style={s.activeDot} />}
              </button>
            );
          })}
        </div>

        {/* Language */}
        {availableLangs.length > 1 && (
          <div style={s.section}>
            <p style={s.sectionLabel}>{t('language')}</p>
            <div style={s.langRow}>
              {availableLangs.map(({ code, name }) => (
                <button key={code} onClick={() => setLang(code)}
                  style={{ ...s.langPill, ...(lang === code ? s.langPillActive : {}) }}>
                  {name}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ML model legend */}
        <div style={s.section}>
          <p style={s.sectionLabel}>{t('forecastModels')}</p>
          {[
            { key: 'RF',  label: 'Random Forest',  color: '#10B981' },
            { key: 'GB',  label: 'Grad. Boosting', color: '#F59E0B' },
            { key: 'XGB', label: 'XGBoost',        color: '#F43F5E' },
          ].map(m => (
            <div key={m.key} style={s.modelItem}>
              <span style={{ ...s.modelDot, background: m.color, boxShadow: `0 0 6px ${m.color}70` }} />
              <span style={s.modelCode}>{m.key}</span>
              <span style={s.modelLabel}>{m.label}</span>
            </div>
          ))}
        </div>

        </div>{/* end scrollArea */}

        {/* User — always pinned to bottom */}
        <div style={s.userSection}>
          {user?.picture
            ? <img src={user.picture} alt="" style={s.avatar} />
            : <div style={s.avatarFallback}>{user?.name?.[0]?.toUpperCase() ?? '?'}</div>
          }
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={s.userName}>{user?.name ?? 'User'}</p>
            <p style={s.userEmail}>{user?.email ?? ''}</p>
          </div>
          <button onClick={signOut} style={s.logoutBtn} title={t('signOut')}>
            <LogOut size={14} />
          </button>
        </div>
      </aside>

      {/* Mobile bottom navigation */}
      <nav className="mobile-nav-bar">
        {NAV.slice(0, 5).map(({ to, icon: Icon, label, color }) => (
          <NavLink key={to} to={to} end={to === '/'} style={({ isActive }) => ({
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
            textDecoration: 'none', padding: '6px 8px',
            color: isActive ? color : '#57534E', fontSize: 9,
            fontFamily: 'var(--font-mono)', letterSpacing: '0.04em',
            transition: 'color 0.15s',
          })}>
            {({ isActive }) => (
              <>
                <Icon size={18} color={isActive ? color : '#57534E'} />
                <span style={{ fontSize: 8 }}>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </>
  );
}

const s = {
  sidebar: {
    width: 230, minWidth: 230, height: '100vh',
    background: 'linear-gradient(180deg, #050508 0%, #080809 100%)',
    borderRight: '1px solid rgba(245,158,11,0.10)',
    display: 'flex', flexDirection: 'column', padding: '18px 0',
    boxShadow: '2px 0 24px rgba(0,0,0,0.55)',
    position: 'relative', zIndex: 10, flexShrink: 0,
  },
  scrollArea: {
    flex: 1, overflowY: 'auto', overflowX: 'hidden',
    scrollbarWidth: 'thin',
    scrollbarColor: 'rgba(245,158,11,0.18) transparent',
  },
  logo: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '0 18px', marginBottom: 24, position: 'relative',
  },
  logoIcon: {
    width: 36, height: 36, background: 'rgba(245,158,11,0.10)',
    border: '1px solid rgba(245,158,11,0.25)', borderRadius: 10,
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
    boxShadow: '0 0 14px rgba(245,158,11,0.15)',
  },
  logoText: {
    fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700,
    letterSpacing: '0.12em', color: 'var(--text-primary)', lineHeight: 1,
  },
  logoSub: {
    fontSize: 8, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)',
    letterSpacing: '0.10em', marginTop: 3, textTransform: 'uppercase',
  },
  connStatus: { marginLeft: 'auto' },

  nav:    { display: 'flex', flexDirection: 'column', gap: 2, padding: '0 10px', marginBottom: 6 },
  navLink: {
    display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px',
    borderRadius: 8, color: 'var(--text-muted)', textDecoration: 'none',
    fontSize: 13, fontWeight: 500, transition: 'all 0.15s ease',
    position: 'relative', fontFamily: 'var(--font-body)',
  },
  navActive: { fontWeight: 600 },
  navIconWrap: {
    width: 26, height: 26, borderRadius: 6, display: 'flex',
    alignItems: 'center', justifyContent: 'center', flexShrink: 0,
    transition: 'all 0.15s ease',
  },
  activeBar: {
    position: 'absolute', right: 0, top: '50%', transform: 'translateY(-50%)',
    width: 3, height: 18, borderRadius: '3px 0 0 3px',
  },

  connCard: {
    margin: '0 10px 6px', padding: '8px 12px',
    background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.18)',
    borderRadius: 8, display: 'flex', alignItems: 'center', gap: 8,
  },
  connLabel: { fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--green)', letterSpacing: '0.12em', fontWeight: 600 },
  connSub:   { fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-muted)', marginTop: 1 },

  section:      { padding: '8px 10px', borderTop: '1px solid rgba(245,158,11,0.07)', marginTop: 2 },
  sectionLabel: {
    fontSize: 8, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)',
    letterSpacing: '0.14em', padding: '0 8px', marginBottom: 6, textTransform: 'uppercase',
  },

  countryBtn: {
    width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px',
    borderRadius: 8, border: '1px solid transparent', background: 'transparent',
    cursor: 'pointer', color: 'var(--text-secondary)', transition: 'all 0.15s ease',
    fontSize: 12, fontFamily: 'var(--font-body)',
  },
  countryActive: {
    background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.22)',
    boxShadow: '0 0 10px rgba(245,158,11,0.07)',
  },
  flag:               { fontSize: 15, lineHeight: 1 },
  countryLabel:       { flex: 1, textAlign: 'left', color: 'var(--text-secondary)', fontSize: 12 },
  countryLabelActive: { color: 'var(--primary)', fontWeight: 600 },
  activeDot: {
    width: 5, height: 5, borderRadius: '50%',
    background: 'var(--primary)', boxShadow: '0 0 7px rgba(245,158,11,0.9)',
  },

  langRow:    { display: 'flex', gap: 5, flexWrap: 'wrap', padding: '0 2px' },
  langPill: {
    padding: '3px 9px', borderRadius: 100, border: '1px solid rgba(245,158,11,0.14)',
    background: 'transparent', color: 'var(--text-muted)',
    fontSize: 10, fontFamily: 'var(--font-mono)', cursor: 'pointer', transition: 'all 0.15s',
  },
  langPillActive: {
    background: 'rgba(245,158,11,0.12)', color: 'var(--primary)',
    borderColor: 'rgba(245,158,11,0.32)', boxShadow: '0 0 8px rgba(245,158,11,0.10)',
  },

  modelItem:  { display: 'flex', alignItems: 'center', gap: 7, padding: '4px 8px' },
  modelDot:   { width: 7, height: 7, borderRadius: '50%', flexShrink: 0 },
  modelCode:  { fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600, color: 'var(--text-secondary)', minWidth: 28 },
  modelLabel: { fontSize: 10, color: 'var(--text-muted)' },

  userSection: {
    flexShrink: 0, padding: '12px 14px', borderTop: '1px solid rgba(245,158,11,0.08)',
    display: 'flex', alignItems: 'center', gap: 9,
  },
  avatar: { width: 30, height: 30, borderRadius: '50%', objectFit: 'cover', border: '1px solid rgba(245,158,11,0.25)' },
  avatarFallback: {
    width: 30, height: 30, borderRadius: '50%',
    background: 'rgba(245,158,11,0.10)', border: '1px solid rgba(245,158,11,0.25)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: 'var(--primary)', fontSize: 13, fontWeight: 600,
  },
  userName:  { fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  userEmail: { fontSize: 9, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' },
  logoutBtn: { background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4, borderRadius: 6, transition: 'color 0.15s', display: 'flex' },
};
