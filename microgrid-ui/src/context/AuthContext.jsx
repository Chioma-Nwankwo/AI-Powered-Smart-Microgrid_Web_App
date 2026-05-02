import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { loginWithGoogle, loginWithMicrosoft, loginWithEmailPassword, registerWithEmailPassword } from '../services/api';
import { msalInstance, loginRequest } from '../services/msalConfig';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore session on mount
  useEffect(() => {
    const stored = localStorage.getItem('gridai_user');
    if (stored) setUser(JSON.parse(stored));
    setLoading(false);
  }, []);

  const saveSession = (userData, jwt) => {
    localStorage.setItem('jwt_token',    jwt);
    localStorage.setItem('gridai_user',  JSON.stringify(userData));
    setUser(userData);
  };

  const IDLE_MS = 30 * 60 * 1000;
  const idleTimer = useRef(null);

  const _signOut = useCallback(() => {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('gridai_user');
    setUser(null);
  }, []);

  const resetIdle = useCallback(() => {
    clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(_signOut, IDLE_MS);
  }, [_signOut]);

  useEffect(() => {
    if (!user) { clearTimeout(idleTimer.current); return; }
    const events = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'];
    events.forEach(e => window.addEventListener(e, resetIdle, { passive: true }));
    resetIdle();
    return () => {
      clearTimeout(idleTimer.current);
      events.forEach(e => window.removeEventListener(e, resetIdle));
    };
  }, [user, resetIdle]);

  // ── Google ──────────────────────────────────────────────────────
  const signInWithGoogle = useCallback(async (credential) => {
    const { data } = await loginWithGoogle(credential);
    saveSession(data.user, data.access_token);
    return { success: true, isNewUser: !!data.is_new_user };
  }, []);

  // ── Microsoft ───────────────────────────────────────────────────
  const signInWithMicrosoft = useCallback(async () => {
    try {
      await msalInstance.initialize();
      const result = await msalInstance.loginPopup(loginRequest);
      const msToken = result.idToken;
      let isNewUser = false;
      try {
        const { data } = await loginWithMicrosoft(msToken);
        saveSession(data.user, data.access_token);
        isNewUser = !!data.is_new_user;
      } catch {
        // Fallback
        const account = result.account;
        const fallbackUser = { name: account.name, email: account.username, picture: null, provider: 'microsoft' };
        saveSession(fallbackUser, msToken);
        isNewUser = true;
      }
      return { success: true, isNewUser };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }, []);

  // ── Email / password ────────────────────────────────────────────
  const loginWithEmail = useCallback(async (email, password) => {
    const { data } = await loginWithEmailPassword(email, password);
    saveSession(data.user, data.access_token);
    return { success: true };
  }, []);

  const registerWithEmail = useCallback(async (email, password) => {
    const { data } = await registerWithEmailPassword(email, password);
    const userData = { email, name: email.split('@')[0], provider: 'email' };
    saveSession(userData, data.access_token);
    return { success: true };
  }, []);

  // ── Sign out ─────────────────────────────────────────────────────
  const signOut = useCallback(() => {
    clearTimeout(idleTimer.current);
    _signOut();
  }, [_signOut]);

  return (
    <AuthContext.Provider value={{ user, loading, signInWithGoogle, signInWithMicrosoft, loginWithEmail, registerWithEmail, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
