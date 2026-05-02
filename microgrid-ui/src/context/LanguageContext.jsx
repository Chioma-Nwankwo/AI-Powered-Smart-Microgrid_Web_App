import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { TRANSLATIONS } from '../i18n/translations';

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(
    () => localStorage.getItem('gridai_lang') || 'en'
  );

  const setLang = useCallback((code) => {
    localStorage.setItem('gridai_lang', code);
    setLangState(code);
  }, []);

  const t = useCallback(
    (key) => TRANSLATIONS[lang]?.[key] ?? TRANSLATIONS.en[key] ?? key,
    [lang]
  );

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);
