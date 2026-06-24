import HeroIllustration from '../components/HeroIllustration.jsx'
import Button from '../ui/Button.jsx'
import Stagger from '../ui/Stagger.jsx'
import ThemeToggle from '../ui/ThemeToggle.jsx'

const FEATURES = [
  { icon: '👁️', title: 'Reads any handwriting',
    desc: 'Gemini Vision transcribes neat or messy student writing — including math symbols.' },
  { icon: '📐', title: 'Step-by-step grading',
    desc: 'Every line of working gets ✓ / ✗ / ⚠ + its own marks. No surprises.' },
  { icon: '🎯', title: 'Finds the root mistake',
    desc: "Identifies the FIRST error — so students don't lose marks on downstream steps." },
  { icon: '✍️', title: 'Handwriting clarity score',
    desc: '1–5 star rating with a specific tip on how to make their writing clearer.' },
  { icon: '🌐', title: 'Hindi + English',
    desc: 'Works for both languages — useful for Hindi-medium answers.' },
  { icon: '📸', title: 'Snap & evaluate',
    desc: 'Use your phone camera or upload a photo. Result in under 8 seconds.' },
]

const STEPS = [
  'Pick the grade, subject and chapter.',
  'Type the question (optional) and the max marks.',
  'Snap a photo of the handwritten answer.',
  'Watch the step-by-step breakdown appear.',
]

export default function Landing({ onStart }) {
  return (
    <div className="landing">
      <nav className="nav">
        <button className="brand" onClick={onStart}>
          <span className="brand-mark">✍️</span>
          <span className="brand-name">Handwritten Answer Evaluator</span>
        </button>
        <div className="nav-right">
          <ThemeToggle />
          <Button variant="ghost" onClick={onStart}>Launch app →</Button>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-text">
          <span className="badge">👁️ Powered By Codevidhya</span>
          <h1>Grade handwritten answers <span className="grad">step by step.</span></h1>
          <p className="lead">
            Snap a photo of a handwritten answer — AI evaluates handwriting +
            correctness + step-by-step marks.
          </p>
          <div className="cta-row">
            <Button variant="primary" size="lg" onClick={onStart} icon="📸">
              Evaluate an answer now
            </Button>
            <Button as="a" variant="ghost" href="#features">How it works ↓</Button>
          </div>
          <div className="trust-row">
            <span>✓ Grade 1 — Grade 12</span>
            <span>✓ Math, Science, English</span>
            <span>✓ Free to use</span>
          </div>
        </div>
        <div className="hero-illustration">
          <HeroIllustration />
        </div>
      </section>

      <section className="features" id="features">
        <h2>Why teachers love it.</h2>
        <Stagger className="feature-grid" gap={70}>
          {FEATURES.map(f => (
            <div className="feature-card" key={f.title}>
              <div className="feature-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </Stagger>
      </section>

      <section className="how" id="how-it-works">
        <h2>How it works</h2>
        <Stagger as="ol" className="steps" gap={90}>
          {STEPS.map((s, i) => (
            <li key={i}>
              <span className="step-num">{i + 1}</span>
              <span>{s}</span>
            </li>
          ))}
        </Stagger>
      </section>

      <section className="final-cta">
        <h2>Fairer marks. Faster.</h2>
        <p>The AI that grades like a real teacher — step by step.</p>
        <Button variant="primary" size="lg" onClick={onStart} icon="📸">
          Launch HandwritingEval
        </Button>
      </section>

      <footer className="foot">
        Handwritten Answer Evaluator · <b>Powered By Codevidhya</b>
      </footer>
    </div>
  )
}
