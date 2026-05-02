import { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth }   from './context/AuthContext';
import Login         from './pages/Login';
import Dashboard     from './pages/Dashboard';
import Settings      from './pages/Settings';
import Onboarding    from './pages/Onboarding';
import ForecastPage  from './pages/ForecastPage';
import OptimizePage  from './pages/OptimizePage';
import AnomalyPage   from './pages/AnomalyPage';

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'100vh', background:'var(--bg-base)' }}>
      <div style={{ width:32, height:32, border:'2px solid var(--border)', borderTop:'2px solid var(--brown)', borderRadius:'50%', animation:'spin 0.7s linear infinite' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
  return user ? children : <Navigate to="/login" replace />;
}

function needsOnboarding(user) {
  if (!user) return false;
  const stored = JSON.parse(localStorage.getItem('gridai_user') || '{}');
  // Completed the wizard at least once
  if (stored.onboarding_completed) return false;
  // Email-signup users who already have a real profile (country + building_type + non-default address)
  if (
    stored.country &&
    stored.building_type &&
    stored.address &&
    stored.address !== 'Not specified'
  ) return false;
  return true;
}

export default function App() {
  const { user } = useAuth();
  // Initialize from the stored user profile so onboarding country selection persists across reloads
  const [country, setCountry] = useState(() => {
    const stored = JSON.parse(localStorage.getItem('gridai_user') || '{}');
    return stored.country?.toLowerCase() || 'nigeria';
  });

  const handleOnboardingComplete = (detectedCountry) => {
    setCountry(detectedCountry);
    const stored = JSON.parse(localStorage.getItem('gridai_user') || '{}');
    localStorage.setItem('gridai_user', JSON.stringify({ ...stored, onboarding_completed: true }));
    window.location.href = '/';
  };

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/onboarding" element={
        <PrivateRoute>
          <Onboarding onComplete={handleOnboardingComplete} />
        </PrivateRoute>
      } />
      <Route path="/settings" element={
        <PrivateRoute>
          {needsOnboarding(user) ? <Navigate to="/onboarding" replace /> :
            <Settings selectedCountry={country} onCountryChange={setCountry} />}
        </PrivateRoute>
      } />
      <Route path="/forecast" element={
        <PrivateRoute>
          {needsOnboarding(user) ? <Navigate to="/onboarding" replace /> :
            <ForecastPage selectedCountry={country} onCountryChange={setCountry} />}
        </PrivateRoute>
      } />
      <Route path="/optimize" element={
        <PrivateRoute>
          {needsOnboarding(user) ? <Navigate to="/onboarding" replace /> :
            <OptimizePage selectedCountry={country} onCountryChange={setCountry} />}
        </PrivateRoute>
      } />
      <Route path="/anomaly" element={
        <PrivateRoute>
          {needsOnboarding(user) ? <Navigate to="/onboarding" replace /> :
            <AnomalyPage selectedCountry={country} onCountryChange={setCountry} />}
        </PrivateRoute>
      } />
      <Route path="/*" element={
        <PrivateRoute>
          {needsOnboarding(user) ? <Navigate to="/onboarding" replace /> :
            <Dashboard selectedCountry={country} onCountryChange={setCountry} />}
        </PrivateRoute>
      } />
    </Routes>
  );
}
