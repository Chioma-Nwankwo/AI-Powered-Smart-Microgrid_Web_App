import { useRef, useEffect, useState, useCallback } from 'react';
import mapboxgl from 'mapbox-gl';
import { COUNTRIES } from '../services/api';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN;

const ISO3 = {
  nigeria: 'NGA', australia: 'AUS', germany: 'DEU', canada: 'CAN',
};

// Map centres per country [lng, lat, zoom]
const VIEWS = {
  nigeria:   [8.6753,  9.0820,  4.2],
  australia: [134.0,  -25.0,    3.2],
  germany:   [10.4515, 51.165,  4.5],
  canada:    [-96.0,   56.5,    3.5],
};

// Microgrid reference locations (capital + installed capacity reference)
const LOCATIONS = {
  nigeria:   { lng: 7.4898,   lat:  9.0579,  city: 'Abuja',    info: 'National Grid · ~4.8 GW capacity' },
  australia: { lng: 149.1300, lat: -35.2809, city: 'Canberra', info: 'NEM · ~52 GW installed'           },
  germany:   { lng: 13.4050,  lat:  52.5200, city: 'Berlin',   info: 'Grid · ~256 GW installed'         },
  canada:    { lng: -75.6972, lat:  45.4215, city: 'Ottawa',   info: 'Grid · ~141 GW installed'         },
};

const FILL_COLORS = {
  NGA: '#C8793F', AUS: '#2471A3', DEU: '#1A7A3F', CAN: '#7B52A8',
};

const GEOJSON_URL =
  'https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson';

export default function MapPanel({ selectedCountry, onCountryChange, userCenter }) {
  const mapContainer = useRef(null);
  const map          = useRef(null);
  const markers      = useRef({});
  const [ready, setReady]   = useState(false);
  const [geoErr, setGeoErr] = useState(false);

  const addCountryLayers = useCallback((geojson) => {
    if (!map.current) return;

    // Filter to just the 4 countries
    const iso3Set = new Set(Object.values(ISO3));
    const filtered = {
      type: 'FeatureCollection',
      features: geojson.features.filter(f =>
        iso3Set.has(f.properties?.ISO_A3 || f.properties?.ADM0_A3)
      ).map(f => ({
        ...f,
        properties: {
          ...f.properties,
          iso3: f.properties.ISO_A3 || f.properties.ADM0_A3,
        },
      })),
    };

    if (map.current.getSource('countries')) {
      map.current.getSource('countries').setData(filtered);
      return;
    }

    map.current.addSource('countries', { type: 'geojson', data: filtered });

    // Base fill (all 4 countries, dim)
    map.current.addLayer({
      id: 'country-fill',
      type: 'fill',
      source: 'countries',
      paint: {
        'fill-color': [
          'match', ['get', 'iso3'],
          'NGA', FILL_COLORS.NGA,
          'AUS', FILL_COLORS.AUS,
          'DEU', FILL_COLORS.DEU,
          'CAN', FILL_COLORS.CAN,
          'transparent',
        ],
        'fill-opacity': 0.28,
      },
    });

    // Selected country bright fill
    map.current.addLayer({
      id: 'country-selected',
      type: 'fill',
      source: 'countries',
      filter: ['==', 'iso3', ISO3[selectedCountry] || ''],
      paint: {
        'fill-color': [
          'match', ['get', 'iso3'],
          'NGA', FILL_COLORS.NGA,
          'AUS', FILL_COLORS.AUS,
          'DEU', FILL_COLORS.DEU,
          'CAN', FILL_COLORS.CAN,
          '#C8793F',
        ],
        'fill-opacity': 0.55,
      },
    });

    // Outline
    map.current.addLayer({
      id: 'country-line',
      type: 'line',
      source: 'countries',
      paint: {
        'line-color': [
          'match', ['get', 'iso3'],
          'NGA', FILL_COLORS.NGA,
          'AUS', FILL_COLORS.AUS,
          'DEU', FILL_COLORS.DEU,
          'CAN', FILL_COLORS.CAN,
          '#888',
        ],
        'line-width': 1.5,
        'line-opacity': 0.8,
      },
    });

    // Click country to select it
    map.current.on('click', 'country-fill', (e) => {
      const iso3 = e.features?.[0]?.properties?.iso3;
      const entry = Object.entries(ISO3).find(([, v]) => v === iso3);
      if (entry) onCountryChange(entry[0]);
    });
    map.current.on('mouseenter', 'country-fill', () => {
      map.current.getCanvas().style.cursor = 'pointer';
    });
    map.current.on('mouseleave', 'country-fill', () => {
      map.current.getCanvas().style.cursor = '';
    });
  }, [onCountryChange, selectedCountry]);

  // Add markers for all 4 capitals
  const addMarkers = useCallback(() => {
    Object.entries(LOCATIONS).forEach(([key, loc]) => {
      if (markers.current[key]) return;
      const el = document.createElement('div');
      el.style.cssText = [
        'width:12px', 'height:12px', 'border-radius:50%',
        `background:${FILL_COLORS[ISO3[key]]}`,
        'border:2px solid #fff', 'box-shadow:0 0 0 2px ' + FILL_COLORS[ISO3[key]] + '44',
        'cursor:pointer', 'transition:transform 0.2s',
      ].join(';');
      el.onmouseenter = () => { el.style.transform = 'scale(1.5)'; };
      el.onmouseleave = () => { el.style.transform = 'scale(1)'; };

      const popup = new mapboxgl.Popup({ offset: 14, closeButton: false, className: 'mapbox-popup-gridai' })
        .setHTML(`
          <div style="font-family:var(--font-mono,monospace);padding:4px 0">
            <p style="font-size:12px;font-weight:700;color:#3d1f05;margin:0 0 3px">${loc.city}</p>
            <p style="font-size:10px;color:#7B4A1C;margin:0">${loc.info}</p>
          </div>
        `);

      markers.current[key] = new mapboxgl.Marker({ element: el })
        .setLngLat([loc.lng, loc.lat])
        .setPopup(popup)
        .addTo(map.current);
    });
  }, []);

  // Init map once
  useEffect(() => {
    if (map.current) return;
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style:     'mapbox://styles/mapbox/dark-v11',
      center:    [20, 10],
      zoom:      1.6,
      projection: 'globe',
      attributionControl: false,
    });

    map.current.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right');

    map.current.on('style.load', () => {
      // Fetch Natural Earth GeoJSON (free, no Mapbox Boundaries plan required)
      fetch(GEOJSON_URL)
        .then(r => r.json())
        .then(geojson => {
          addCountryLayers(geojson);
          addMarkers();
          setReady(true);
        })
        .catch(err => {
          logger.error('GeoJSON fetch failed', err);
          setGeoErr(true);
          addMarkers();
          setReady(true);
        });
    });

    return () => {
      Object.values(markers.current).forEach(m => m.remove());
      markers.current = {};
      map.current?.remove();
      map.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fly to user's saved state-level location once on first ready
  useEffect(() => {
    if (!ready || !map.current || !userCenter) return;
    map.current.flyTo({ center: userCenter, zoom: 10, duration: 1800, essential: true });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  // Update selected-country highlight and fly to it
  useEffect(() => {
    if (!ready || !map.current) return;
    const iso3 = ISO3[selectedCountry] || '';
    if (map.current.getLayer('country-selected')) {
      map.current.setFilter('country-selected', ['==', 'iso3', iso3]);
    }
    const [, , zoom] = VIEWS[selectedCountry] || [20, 10, 1.6];
    const { lng: cLng, lat: cLat } = LOCATIONS[selectedCountry] || { lng: 20, lat: 0 };
    map.current.flyTo({ center: [cLng, cLat], zoom, duration: 1400, essential: true });

    // Pulse the active marker
    Object.entries(markers.current).forEach(([key, marker]) => {
      const el = marker.getElement();
      el.style.transform = key === selectedCountry ? 'scale(1.6)' : 'scale(1)';
    });
  }, [selectedCountry, ready]);

  const country = COUNTRIES[selectedCountry];

  return (
    <div style={styles.wrapper}>
      <div ref={mapContainer} style={styles.map} />

      {/* Country label overlay */}
      <div style={styles.overlay}>
        <div style={styles.countryTag}>
          <span style={{ fontSize: 18 }}>{country?.flag}</span>
          <span style={styles.countryName}>{country?.label}</span>
          <div className="pulse-dot" />
        </div>
      </div>

      {/* GeoJSON error notice */}
      {geoErr && (
        <div style={styles.geoErrBadge}>Map fills unavailable (network)</div>
      )}

      {/* Country quick-select chips */}
      <div style={styles.chips}>
        {Object.entries(COUNTRIES).map(([key, { flag, label }]) => (
          <button
            key={key}
            onClick={() => onCountryChange(key)}
            style={{
              ...styles.chip,
              ...(selectedCountry === key ? {
                ...styles.chipActive,
                borderColor: FILL_COLORS[ISO3[key]],
                color: FILL_COLORS[ISO3[key]],
                background: FILL_COLORS[ISO3[key]] + '18',
              } : {}),
            }}
          >
            {flag} {label}
          </button>
        ))}
      </div>

      {/* Legend */}
      <div style={styles.legend}>
        {Object.entries(LOCATIONS).map(([key, loc]) => (
          <div key={key} style={styles.legendItem} onClick={() => onCountryChange(key)}>
            <span style={{ ...styles.legendDot, background: FILL_COLORS[ISO3[key]] }} />
            <span style={styles.legendCity}>{loc.city}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// suppress console.error for the logger reference in catch
const logger = { error: (...a) => console.error(...a) };

const styles = {
  wrapper: {
    position: 'relative', width: '100%', height: '100%',
    borderRadius: 12, overflow: 'hidden', border: '1px solid rgba(245,158,11,0.14)',
    boxShadow: '0 0 20px rgba(245,158,11,0.07)',
  },
  map: { width: '100%', height: '100%' },
  overlay: { position: 'absolute', top: 12, left: 12, pointerEvents: 'none' },
  countryTag: {
    display: 'flex', alignItems: 'center', gap: 8,
    background: 'rgba(15,15,20,0.90)', backdropFilter: 'blur(12px)',
    border: '1px solid rgba(245,158,11,0.22)', borderRadius: 8, padding: '7px 12px',
    boxShadow: '0 0 12px rgba(245,158,11,0.10)',
  },
  countryName: {
    fontFamily: 'var(--font-display)', fontSize: 15, fontWeight: 600, color: '#F59E0B',
  },
  geoErrBadge: {
    position: 'absolute', top: 12, right: 50,
    background: 'rgba(176,58,46,0.85)', color: '#fff',
    fontSize: 10, fontFamily: 'var(--font-mono)', padding: '4px 10px',
    borderRadius: 6, pointerEvents: 'none',
  },
  chips: {
    position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)',
    display: 'flex', gap: 6,
  },
  chip: {
    padding: '5px 12px', borderRadius: 100, border: '1px solid rgba(245,158,11,0.16)',
    background: 'rgba(15,15,20,0.88)', backdropFilter: 'blur(8px)',
    color: 'var(--text-secondary)', fontSize: 11, fontWeight: 500,
    cursor: 'pointer', transition: 'all 0.15s ease', whiteSpace: 'nowrap',
    fontFamily: 'var(--font-mono)',
  },
  chipActive: { fontWeight: 700 },
  legend: {
    position: 'absolute', bottom: 52, right: 12,
    background: 'rgba(15,15,20,0.90)', backdropFilter: 'blur(10px)',
    border: '1px solid rgba(245,158,11,0.16)', borderRadius: 8, padding: '8px 12px',
    display: 'flex', flexDirection: 'column', gap: 6,
    boxShadow: '0 0 12px rgba(245,158,11,0.08)',
  },
  legendItem: {
    display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
  },
  legendDot: { width: 8, height: 8, borderRadius: '50%', flexShrink: 0 },
  legendCity: { fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' },
};
