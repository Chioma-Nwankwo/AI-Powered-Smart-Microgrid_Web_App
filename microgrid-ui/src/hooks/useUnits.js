import { useState, useEffect } from 'react';

export default function useUnits() {
  const [units, setUnits] = useState(
    () => localStorage.getItem('gridai_units') || 'metric'
  );

  useEffect(() => {
    const handler = () =>
      setUnits(localStorage.getItem('gridai_units') || 'metric');
    window.addEventListener('gridai-units-changed', handler);
    return () => window.removeEventListener('gridai-units-changed', handler);
  }, []);

  const isImperial = units === 'imperial';

  const tempStr  = (celsius) =>
    isImperial
      ? `${(celsius * 9 / 5 + 32).toFixed(1)}°F`
      : `${parseFloat(celsius).toFixed(1)}°C`;

  const windStr  = (mps) =>
    isImperial
      ? `${(mps * 2.23694).toFixed(1)} mph`
      : `${(mps * 3.6).toFixed(1)} km/h`;

  const windUnit = isImperial ? 'mph' : 'm/s';
  const windLabel = isImperial ? 'Wind (mph)' : 'Wind (m/s)';

  return { units, isImperial, tempStr, windStr, windUnit, windLabel };
}
