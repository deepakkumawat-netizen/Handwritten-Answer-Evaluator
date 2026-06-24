// Inline SVG hero — handwritten notebook + pen + step-by-step check marks
export default function HeroIllustration() {
  return (
    <svg viewBox="0 0 600 480" xmlns="http://www.w3.org/2000/svg" className="hero-svg">
      <defs>
        <linearGradient id="bgGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%"  stopColor="#10b981" stopOpacity="0.18"/>
          <stop offset="100%" stopColor="#14b8a6" stopOpacity="0.05"/>
        </linearGradient>
        <linearGradient id="penGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%"  stopColor="#0f766e"/>
          <stop offset="100%" stopColor="#134e4a"/>
        </linearGradient>
        <linearGradient id="camGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%"  stopColor="#10b981"/>
          <stop offset="100%" stopColor="#059669"/>
        </linearGradient>
        <filter id="softShadow2">
          <feDropShadow dx="0" dy="6" stdDeviation="8" floodOpacity="0.12"/>
        </filter>
      </defs>

      <circle cx="300" cy="240" r="220" fill="url(#bgGrad)"/>

      {/* Notebook page */}
      <g filter="url(#softShadow2)">
        <rect x="110" y="90" width="320" height="320" rx="10" fill="#fff"
              stroke="#cbd5e1" strokeWidth="1.5"/>
        {/* Spiral binding */}
        <g fill="#94a3b8">
          {[110, 145, 180, 215, 250, 285, 320, 355, 390].map((y) => (
            <circle key={y} cx="115" cy={y} r="3.5"/>
          ))}
        </g>
        {/* Page lines */}
        <g stroke="#e2e8f0" strokeWidth="1">
          {Array.from({ length: 9 }, (_, i) => 130 + i * 30).map((y) => (
            <line key={y} x1="135" y1={y} x2="415" y2={y}/>
          ))}
        </g>
      </g>

      {/* "Handwritten" steps */}
      <g fontFamily="Caveat, 'Comic Sans MS', cursive" fontSize="22" fill="#1e293b">
        <text x="150" y="160">Step 1: 2x + 3 = 7</text>
        <text x="150" y="220">Step 2: 2x = 4</text>
        <text x="150" y="280">Step 3: x = 2</text>
      </g>

      {/* Step status icons */}
      <g>
        {/* Step 1: correct */}
        <circle cx="375" cy="153" r="14" fill="#10b981"/>
        <path d="M368 154 L373 159 L383 148" stroke="#fff" strokeWidth="3"
              strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        {/* Step 2: partial */}
        <circle cx="375" cy="213" r="14" fill="#f59e0b"/>
        <text x="375" y="220" textAnchor="middle" fill="#fff" fontSize="20" fontWeight="700">!</text>
        {/* Step 3: correct */}
        <circle cx="375" cy="273" r="14" fill="#10b981"/>
        <path d="M368 274 L373 279 L383 268" stroke="#fff" strokeWidth="3"
              strokeLinecap="round" strokeLinejoin="round" fill="none"/>
      </g>

      {/* Score badge bottom of page */}
      <g transform="translate(180, 330)">
        <rect width="200" height="50" rx="10" fill="#ecfdf5" stroke="#10b981" strokeWidth="2"/>
        <text x="100" y="32" textAnchor="middle" fill="#065f46" fontSize="20"
              fontFamily="Plus Jakarta Sans, sans-serif" fontWeight="800">
          4 / 5  ★★★★☆
        </text>
      </g>

      {/* Pen */}
      <g transform="translate(420, 60) rotate(35)" filter="url(#softShadow2)">
        <rect x="0"  y="0"  width="14" height="180" rx="3" fill="url(#penGrad)"/>
        <rect x="-2" y="0"  width="18" height="16" rx="3" fill="#0f766e"/>
        <polygon points="0,180 14,180 7,210" fill="#0f172a"/>
        <line x1="7" y1="190" x2="7" y2="208" stroke="#fde047" strokeWidth="2"/>
      </g>

      {/* Camera/phone icon top-left */}
      <g transform="translate(40, 70)" filter="url(#softShadow2)">
        <rect width="78" height="78" rx="14" fill="url(#camGrad)"/>
        <circle cx="39" cy="39" r="20" fill="#fff"/>
        <circle cx="39" cy="39" r="14" fill="#10b981"/>
        <circle cx="39" cy="39" r="8"  fill="#fff"/>
        <rect x="56" y="14" width="14" height="8" rx="3" fill="#fff"/>
      </g>

      {/* Sparkles */}
      <g fill="#fde047">
        <path d="M520 200 l5 -12 l5 12 l12 5 l-12 5 l-5 12 l-5 -12 l-12 -5 z"/>
        <path d="M60 380 l4 -9 l4 9 l9 4 l-9 4 l-4 9 l-4 -9 l-9 -4 z"/>
      </g>
    </svg>
  )
}
