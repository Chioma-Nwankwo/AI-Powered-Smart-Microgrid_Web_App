/**
 * GridBackground — Solar Plasma Field
 * Rising amber energy particles + AC power sine wave + drifting glow orbs.
 */

const PARTICLES = [
  { x: 80,   r: 2.4, color: '#F59E0B', opacity: 0.55, dur: 9,  delay: 0,   drift:  18 },
  { x: 195,  r: 1.6, color: '#F59E0B', opacity: 0.35, dur: 12, delay: 1.8, drift: -14 },
  { x: 310,  r: 3.0, color: '#10B981', opacity: 0.40, dur: 8,  delay: 3.2, drift:  12 },
  { x: 430,  r: 1.4, color: '#F59E0B', opacity: 0.30, dur: 14, delay: 0.6, drift: -10 },
  { x: 555,  r: 2.0, color: '#F59E0B', opacity: 0.48, dur: 10, delay: 5.0, drift:  16 },
  { x: 665,  r: 2.8, color: '#10B981', opacity: 0.38, dur: 7,  delay: 2.5, drift: -18 },
  { x: 780,  r: 1.6, color: '#F59E0B', opacity: 0.42, dur: 11, delay: 0.3, drift:  10 },
  { x: 890,  r: 3.2, color: '#FBBF24', opacity: 0.28, dur: 9,  delay: 4.1, drift: -12 },
  { x: 1010, r: 2.0, color: '#10B981', opacity: 0.35, dur: 13, delay: 1.0, drift:  14 },
  { x: 1120, r: 2.6, color: '#F59E0B', opacity: 0.52, dur: 8,  delay: 6.0, drift: -16 },
  { x: 1240, r: 1.8, color: '#F59E0B', opacity: 0.38, dur: 10, delay: 3.8, drift:  12 },
  { x: 1360, r: 2.2, color: '#10B981', opacity: 0.45, dur: 11, delay: 0.9, drift: -10 },
  { x: 155,  r: 2.0, color: '#FBBF24', opacity: 0.32, dur: 15, delay: 7.0, drift:  20 },
  { x: 380,  r: 2.8, color: '#F59E0B', opacity: 0.44, dur: 9,  delay: 2.2, drift: -14 },
  { x: 500,  r: 1.5, color: '#10B981', opacity: 0.30, dur: 12, delay: 5.5, drift:  10 },
  { x: 730,  r: 3.0, color: '#F59E0B', opacity: 0.40, dur: 8,  delay: 1.5, drift: -20 },
  { x: 850,  r: 1.8, color: '#F59E0B', opacity: 0.55, dur: 10, delay: 3.5, drift:  16 },
  { x: 950,  r: 2.4, color: '#10B981', opacity: 0.35, dur: 13, delay: 0.7, drift: -12 },
  { x: 1070, r: 1.6, color: '#FBBF24', opacity: 0.48, dur: 7,  delay: 4.8, drift:  14 },
  { x: 1300, r: 2.8, color: '#F59E0B', opacity: 0.38, dur: 9,  delay: 2.8, drift: -18 },
];

export default function GridBackground() {
  return (
    <svg
      style={{
        position: 'fixed', inset: 0,
        width: '100%', height: '100%',
        pointerEvents: 'none', zIndex: 0,
      }}
      viewBox="0 0 1440 900"
      preserveAspectRatio="xMidYMid slice"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <filter id="amber-glow" x="-120%" y="-120%" width="340%" height="340%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="wave-blur" x="-5%" y="-80%" width="110%" height="260%">
          <feGaussianBlur stdDeviation="3.5" />
        </filter>
        <radialGradient id="amber-orb" cx="50%" cy="50%" r="50%">
          <stop offset="0%"   stopColor="#F59E0B" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#F59E0B" stopOpacity="0"    />
        </radialGradient>
        <radialGradient id="emerald-orb" cx="50%" cy="50%" r="50%">
          <stop offset="0%"   stopColor="#10B981" stopOpacity="0.14" />
          <stop offset="100%" stopColor="#10B981" stopOpacity="0"    />
        </radialGradient>
        <radialGradient id="gold-orb" cx="50%" cy="50%" r="50%">
          <stop offset="0%"   stopColor="#FBBF24" stopOpacity="0.11" />
          <stop offset="100%" stopColor="#FBBF24" stopOpacity="0"    />
        </radialGradient>
      </defs>

      {/* Drifting ambient glow orbs */}
      <ellipse cx="280" cy="620" rx="430" ry="370" fill="url(#amber-orb)">
        <animateTransform attributeName="transform" type="translate"
          values="0 0; 180 -120; -60 80; 0 0" dur="24s" repeatCount="indefinite"
          calcMode="spline" keySplines="0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1" />
      </ellipse>
      <ellipse cx="1160" cy="220" rx="410" ry="350" fill="url(#emerald-orb)">
        <animateTransform attributeName="transform" type="translate"
          values="0 0; -140 90; 100 -70; 0 0" dur="30s" repeatCount="indefinite"
          calcMode="spline" keySplines="0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1" />
      </ellipse>
      <ellipse cx="720" cy="450" rx="260" ry="210" fill="url(#gold-orb)">
        <animateTransform attributeName="transform" type="translate"
          values="0 0; 80 -50; -60 40; 0 0" dur="20s" repeatCount="indefinite"
          calcMode="spline" keySplines="0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1" />
      </ellipse>

      {/* AC sine wave — blurred shadow */}
      <g filter="url(#wave-blur)" opacity="0.38">
        <path
          d="M-480,832 Q-360,778 -240,832 Q-120,886 0,832 Q120,778 240,832 Q360,886 480,832 Q600,778 720,832 Q840,886 960,832 Q1080,778 1200,832 Q1320,886 1440,832 Q1560,778 1680,832 Q1800,886 1920,832"
          fill="none" stroke="#F59E0B" strokeWidth="2.5"
        >
          <animateTransform attributeName="transform" type="translate"
            from="480 0" to="0 0" dur="3.5s" repeatCount="indefinite" />
        </path>
      </g>
      {/* Crisp amber wave */}
      <path
        d="M-480,832 Q-360,778 -240,832 Q-120,886 0,832 Q120,778 240,832 Q360,886 480,832 Q600,778 720,832 Q840,886 960,832 Q1080,778 1200,832 Q1320,886 1440,832 Q1560,778 1680,832 Q1800,886 1920,832"
        fill="none" stroke="rgba(245,158,11,0.48)" strokeWidth="1.5"
      >
        <animateTransform attributeName="transform" type="translate"
          from="480 0" to="0 0" dur="3.5s" repeatCount="indefinite" />
      </path>
      {/* Emerald secondary wave */}
      <path
        d="M-480,860 Q-360,826 -240,860 Q-120,894 0,860 Q120,826 240,860 Q360,894 480,860 Q600,826 720,860 Q840,894 960,860 Q1080,826 1200,860 Q1320,894 1440,860 Q1560,826 1680,860 Q1800,894 1920,860"
        fill="none" stroke="rgba(16,185,129,0.28)" strokeWidth="1"
      >
        <animateTransform attributeName="transform" type="translate"
          from="0 0" to="-480 0" dur="4.5s" repeatCount="indefinite" />
      </path>

      {/* Rising energy particles */}
      {PARTICLES.map((p, i) => (
        <circle key={i} cx={p.x} r={p.r} fill={p.color} filter="url(#amber-glow)">
          <animate attributeName="cy" from="910" to="-10"
            dur={`${p.dur}s`} begin={`${p.delay}s`} repeatCount="indefinite" />
          <animate attributeName="opacity"
            values={`0; ${p.opacity}; ${p.opacity}; 0`}
            keyTimes="0; 0.08; 0.85; 1"
            dur={`${p.dur}s`} begin={`${p.delay}s`} repeatCount="indefinite" />
          <animate attributeName="cx"
            values={`${p.x}; ${p.x + p.drift}; ${p.x}`}
            dur={`${p.dur * 0.7}s`} begin={`${p.delay}s`} repeatCount="indefinite"
            calcMode="spline" keySplines="0.4 0 0.6 1;0.4 0 0.6 1" />
        </circle>
      ))}
    </svg>
  );
}
