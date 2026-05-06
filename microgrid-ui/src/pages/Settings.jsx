import { useState } from 'react';
import { useAuth }     from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { TRANSLATIONS, LANGUAGE_NAMES } from '../i18n/translations';
import { Settings as SettingsIcon, User, Globe, Sliders, LogOut, Edit2, Zap } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import ApplianceCalculator from '../components/ApplianceCalculator';
import { updateProfile } from '../services/api';
import { useNavigate, useLocation } from 'react-router-dom';

// Country selector re-exported so Settings page can control it too
export default function Settings({ selectedCountry, onCountryChange }) {
  const { user, signOut } = useAuth();
  const { lang, setLang, t }  = useLanguage();
  const navigate   = useNavigate();
  const [saved, setSaved]             = useState(false);
  const [units, setUnits]             = useState(localStorage.getItem('gridai_units') || 'metric');
  const [applianceSaved, setApplianceSaved] = useState(false);
  const [applianceSaving, setApplianceSaving] = useState(false);

  const profile = (() => {
    try { return JSON.parse(localStorage.getItem('gridai_user') || '{}'); } catch { return {}; }
  })();
  const [applianceData, setApplianceData] = useState({
    appliances: profile.appliances || [],
    peak_kw:    profile.peak_demand_kw || 0,
    daily_kwh:  profile.daily_kwh || 0,
  });

  const handleSave = () => {
    localStorage.setItem('gridai_units', units);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleSaveAppliances = async () => {
    setApplianceSaving(true);
    try {
      await updateProfile({
        appliances:     applianceData.appliances,
        peak_demand_kw: applianceData.peak_kw,
        daily_kwh:      applianceData.daily_kwh,
      });
      const stored = JSON.parse(localStorage.getItem('gridai_user') || '{}');
      localStorage.setItem('gridai_user', JSON.stringify({
        ...stored,
        appliances:     applianceData.appliances,
        peak_demand_kw: applianceData.peak_kw,
        daily_kwh:      applianceData.daily_kwh,
      }));
      setApplianceSaved(true);
      setTimeout(() => setApplianceSaved(false), 2000);
    } catch {
      // silent fail — user can retry
    } finally {
      setApplianceSaving(false);
    }
  };

  const handleSignOut = () => {
    if (window.confirm(t('signOutConfirm'))) {
      signOut();
      navigate('/login');
    }
  };

  const allLangs = Object.entries(LANGUAGE_NAMES).map(([code, name]) => ({ code, name }));

  return (
    <div style={s.shell}>
      <Sidebar selectedCountry={selectedCountry} onCountryChange={onCountryChange} />

      <main style={s.main}>
        {/* Top bar */}
        <header style={s.topBar}>
          <div style={s.titleRow}>
            <SettingsIcon size={16} color="var(--brown)" />
            <h1 style={s.pageTitle}>{t('settings')}</h1>
          </div>
        </header>

        <div style={s.content}>

          {/* Profile card */}
          <section style={s.card}>
            <div style={s.cardHeader}>
              <User size={15} color="var(--brown)" />
              <span style={s.cardTitle}>{t('profile')}</span>
            </div>
            <div style={s.profileRow}>
              {user?.picture
                ? <img src={user.picture} alt="" style={s.avatar} />
                : (
                  <div style={s.avatarFallback}>
                    {user?.name?.[0]?.toUpperCase() ?? '?'}
                  </div>
                )
              }
              <div style={{ flex: 1 }}>
                <p style={s.profileName}>{user?.name ?? 'User'}</p>
                <p style={s.profileEmail}>{user?.email ?? ''}</p>
                <p style={s.profileMeta}>{user?.country ?? ''} {user?.building_type ? `· ${user.building_type}` : ''}</p>
              </div>
            </div>
            <button onClick={() => navigate('/onboarding')} style={s.editProfileBtn}>
              <Edit2 size={12} />
              Edit Grid Profile
            </button>
          </section>

          {/* Language card */}
          <section style={s.card}>
            <div style={s.cardHeader}>
              <Globe size={15} color="var(--brown)" />
              <span style={s.cardTitle}>{t('language')}</span>
            </div>
            <p style={s.cardDesc}>
              Choose the display language for the dashboard.
            </p>
            <div style={s.langGrid}>
              {allLangs.map(({ code, name }) => (
                <button
                  key={code}
                  onClick={() => setLang(code)}
                  style={{ ...s.langBtn, ...(lang === code ? s.langBtnActive : {}) }}
                >
                  {name}
                  {lang === code && <span style={s.checkmark}>✓</span>}
                </button>
              ))}
            </div>
          </section>

          {/* Preferences card */}
          <section style={s.card}>
            <div style={s.cardHeader}>
              <Sliders size={15} color="var(--brown)" />
              <span style={s.cardTitle}>{t('preferences')}</span>
            </div>

            <div style={s.prefRow}>
              <label style={s.prefLabel}>{t('units')}</label>
              <div style={s.radioGroup}>
                {['metric', 'imperial'].map(u => (
                  <label key={u} style={s.radioLabel}>
                    <input
                      type="radio"
                      name="units"
                      value={u}
                      checked={units === u}
                      onChange={() => setUnits(u)}
                      style={{ accentColor: 'var(--brown)' }}
                    />
                    {t(u)}
                  </label>
                ))}
              </div>
            </div>

            <button onClick={handleSave} style={s.saveBtn}>
              {saved ? `✓ ${t('saved')}` : t('saveChanges')}
            </button>
          </section>

          {/* Appliances card */}
          <section style={s.card}>
            <div style={s.cardHeader}>
              <Zap size={15} color="var(--brown)" />
              <span style={s.cardTitle}>Your Appliances</span>
            </div>
            <p style={s.cardDesc}>
              Update your appliance list to get accurate load estimates and personalised battery sizing.
            </p>
            <ApplianceCalculator
              buildingType={profile.building_type || 'residential'}
              value={applianceData.appliances}
              onChange={(appliances, peak_kw, daily_kwh) =>
                setApplianceData({ appliances, peak_kw, daily_kwh })
              }
            />
            <button
              onClick={handleSaveAppliances}
              disabled={applianceSaving}
              style={{ ...s.saveBtn, marginTop: 14 }}
            >
              {applianceSaved ? '✓ Saved' : applianceSaving ? 'Saving…' : 'Save Appliances'}
            </button>
          </section>

          {/* Sign out */}
          <button onClick={handleSignOut} style={s.signOutBtn}>
            <LogOut size={14} />
            {t('signOut')}
          </button>

        </div>
      </main>
    </div>
  );
}

const s = {
  shell:   { display: 'flex', height: '100vh', overflow: 'hidden' },
  main:    { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg-base)' },
  topBar:  {
    display: 'flex', alignItems: 'center', padding: '12px 20px',
    borderBottom: '1px solid var(--border)', background: 'var(--bg-card)',
    boxShadow: 'var(--shadow-up)', flexShrink: 0,
  },
  titleRow: { display: 'flex', alignItems: 'center', gap: 9 },
  pageTitle: { fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' },

  content: {
    flex: 1, overflowY: 'auto', padding: 20,
    display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 560,
  },

  card: {
    background: 'var(--bg-card)', border: '1px solid var(--border)',
    borderRadius: 14, padding: '20px 22px', boxShadow: 'var(--shadow-card)',
  },
  cardHeader: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 },
  cardTitle:  { fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', letterSpacing: '0.08em', textTransform: 'uppercase' },
  cardDesc:   { fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 },

  profileRow:     { display: 'flex', alignItems: 'center', gap: 14 },
  avatar:         { width: 48, height: 48, borderRadius: '50%', objectFit: 'cover' },
  avatarFallback: {
    width: 48, height: 48, borderRadius: '50%', background: 'var(--brown-dim)',
    border: '1px solid var(--border-bright)', display: 'flex', alignItems: 'center',
    justifyContent: 'center', color: 'var(--brown)', fontSize: 18, fontWeight: 700,
  },
  profileName:  { fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 },
  profileEmail: { fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginBottom: 2 },
  profileMeta:  { fontSize: 11, color: 'var(--text-muted)', textTransform: 'capitalize' },

  langGrid: { display: 'flex', flexWrap: 'wrap', gap: 8 },
  langBtn:  {
    padding: '8px 16px', borderRadius: 9, border: '1px solid var(--border)',
    background: 'var(--bg-elevated)', color: 'var(--text-secondary)',
    fontFamily: 'var(--font-body)', fontSize: 13, cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.15s',
  },
  langBtnActive: {
    background: 'var(--brown)', color: '#fff',
    borderColor: 'var(--brown)',
  },
  checkmark: { fontSize: 12 },

  prefRow:    { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 },
  prefLabel:  { fontSize: 13, color: 'var(--text-primary)', fontWeight: 500 },
  radioGroup: { display: 'flex', gap: 16 },
  radioLabel: { display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer' },

  saveBtn: {
    padding: '10px 20px', borderRadius: 9, border: 'none',
    background: 'var(--brown)', color: '#fff',
    fontFamily: 'var(--font-body)', fontSize: 13, fontWeight: 600, cursor: 'pointer',
  },

  editProfileBtn: {
    display: 'flex', alignItems: 'center', gap: 6, marginTop: 14,
    padding: '8px 16px', borderRadius: 8, border: '1px solid rgba(245,158,11,0.28)',
    background: 'rgba(245,158,11,0.07)', color: 'var(--primary)',
    fontFamily: 'var(--font-body)', fontSize: 12, fontWeight: 600, cursor: 'pointer',
    width: 'fit-content', transition: 'all 0.15s',
  },
  signOutBtn: {
    display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px',
    borderRadius: 9, border: '1px solid var(--border)',
    background: 'var(--bg-card)', color: 'var(--red)',
    fontFamily: 'var(--font-body)', fontSize: 13, fontWeight: 500, cursor: 'pointer',
    width: 'fit-content',
  },
};
