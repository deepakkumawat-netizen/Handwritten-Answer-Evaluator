import { useEffect, useMemo, useState } from 'react'
import Button from '../ui/Button.jsx'
import Card from '../ui/Card.jsx'
import Field from '../ui/Field.jsx'
import FileDropzone from '../ui/FileDropzone.jsx'
import MarksSlider from '../ui/MarksSlider.jsx'
import Skeleton from '../ui/Skeleton.jsx'
import ThemeToggle from '../ui/ThemeToggle.jsx'
import HistoryModal from '../components/HistoryModal.jsx'
import { useApi } from '../hooks/useApi.js'
import { useToast } from '../hooks/useToast.js'

const VERDICT_ICON = { correct: '✓', wrong: '✗', partial: '⚠' }

export default function Evaluator({ onHome }) {
  const { push } = useToast()
  const [question, setQ]      = useState('')
  const [maxMarks, setMax]    = useState(5)
  const [files, setFiles]     = useState([])
  const [showMarks, setShowMarks] = useState(false)
  const [openIdx, setOpenIdx] = useState(0)
  const [health, setHealth]   = useState(null)

  useEffect(() => {
    fetch('/api/health').then(r => r.json()).then(setHealth).catch(() => setHealth({}))
  }, [])

  const hasAnyPdf = files.some(f => f.type === 'application/pdf' || f.name?.toLowerCase().endsWith('.pdf'))
  const isSingle  = files.length === 1
  const firstFile = files[0] || null
  const firstIsPdf = firstFile && (firstFile.type === 'application/pdf' || firstFile.name?.toLowerCase().endsWith('.pdf'))
  const firstIsImage = firstFile && !firstIsPdf && (firstFile.type?.startsWith('image/') || /\.(jpg|jpeg|png|webp)$/i.test(firstFile.name || ''))
  const preview = useMemo(() => (isSingle && firstIsImage ? URL.createObjectURL(firstFile) : ''), [isSingle, firstIsImage, firstFile])
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview])

  // PDFs always carry marks on the sheet — auto-enable
  useEffect(() => { if (hasAnyPdf) setShowMarks(true) }, [hasAnyPdf])

  const evalApi = useApi(async (signal) => {
    const fd = new FormData()
    fd.append('question', question)
    fd.append('max_marks', String(maxMarks))
    files.forEach(f => fd.append('image', f, f.name))
    const r = await fetch('/api/grade/handwriting', { method: 'POST', body: fd, signal })
    if (!r.ok) throw new Error(`HTTP ${r.status}: ${(await r.text()).slice(0, 200)}`)
    return r.json()
  })

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && !evalApi.loading) submit()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [files, question, maxMarks, evalApi.loading])

  const submit = async () => {
    if (!files.length) { push({ kind: 'error', title: 'No files yet', body: 'Drop or upload one or more handwritten answers.' }); return }
    setOpenIdx(0)
    try {
      const r = await evalApi.run()
      push({
        kind: 'success',
        title: `Evaluated ${r.graded}/${r.count}`,
        body: r.graded === r.count ? 'All answers processed' : `${r.count - r.graded} failed`,
      })
    } catch (e) {
      push({ kind: 'error', title: 'Evaluation failed', body: String(e.message || e) })
    }
  }

  const missingGemini = health && !health.gemini_configured

  // History modal
  const [histOpen, setHistOpen] = useState(false)
  const [histCount, setHistCount] = useState(0)
  useEffect(() => {
    fetch('/api/history').then(r => r.json()).then(d => setHistCount((d.items || []).length)).catch(() => {})
  }, [evalApi.data])
  const loadFromHistory = (entry) => {
    evalApi.setData(entry.payload)
    setHistOpen(false)
    push({ kind: 'success', title: 'Loaded from history', body: entry.title })
  }
  const report = evalApi.data
  const canSubmit = !evalApi.loading && files.length > 0

  return (
    <div className="app-wrap">
      <header className="app-bar">
        <button className="brand" onClick={onHome}>
          <span className="brand-mark">✍️</span>
          <span className="brand-name">Handwritten Answer Evaluator</span>
        </button>
        <div className="app-bar-right">
          <span className="muted">Handwriting + correctness + step-by-step · Powered By Codevidhya</span>
          <button className="hist-btn" onClick={() => setHistOpen(true)}>
            <span>🗂</span><span>History</span>
            {histCount > 0 && <span className="hist-btn-badge">{histCount}</span>}
          </button>
          <ThemeToggle size="sm" />
          <Button variant="ghost" size="sm" onClick={onHome}>← Home</Button>
        </div>
      </header>

      {missingGemini && (
        <div className="banner">⚠️ GEMINI_API_KEY missing — edit backend/.env and restart.</div>
      )}

      <main className="page">
        <div className="auto-detect-info">
          <span className="ad-icon">🪄</span>
          <div>
            <b>Bulk mode — upload up to 30 sheets at once.</b> Each answer is auto-detected
            (grade, subject, chapter) and evaluated independently.
          </div>
        </div>

        <Card>
          <Card.Header
            eyebrow="Step 1"
            title="Question & marks"
            hint={
              !files.length
                ? 'Upload one or more answer sheets below — marks options appear once files are added'
                : hasAnyPdf
                  ? 'PDF detected — marks read directly from the answer sheet'
                  : (showMarks
                      ? 'Marks enabled — use the slider below'
                      : 'Marks are off. Turn on the toggle if you want a numeric score.')
            }
          />
          <Card.Body>
            <Field label="Question (optional)" wide>
              {({ id }) => (
                <input id={id} value={question} onChange={e => setQ(e.target.value)}
                       placeholder="e.g. Solve 2x + 3 = 11 — or leave blank for mixed-question sheets"
                       disabled={evalApi.loading}/>
              )}
            </Field>

            {files.length > 0 && !hasAnyPdf && (
              <label className="verify-toggle">
                <input type="checkbox" checked={showMarks}
                       onChange={e => setShowMarks(e.target.checked)}
                       disabled={evalApi.loading}/>
                <div>
                  <div className="vt-title">📊 Show marks in result</div>
                  <div className="vt-sub">Off by default — turn on to display a numeric score + per-step marks.</div>
                </div>
              </label>
            )}

            {hasAnyPdf && (
              <div className="pdf-marks-note">
                <span className="pmn-icon">📄</span>
                <div>
                  <div className="pmn-title">Marks auto-detected from PDF(s)</div>
                  <div className="pmn-sub">Marks read directly from each sheet — no need to set a max.</div>
                </div>
              </div>
            )}
            {files.length > 0 && !hasAnyPdf && showMarks && (
              <Field label={`Max marks per answer: ${maxMarks}`}>
                {() => <MarksSlider value={maxMarks} onChange={setMax} disabled={evalApi.loading} />}
              </Field>
            )}
          </Card.Body>
        </Card>

        <Card>
          <Card.Header eyebrow="Step 2" title="Handwritten answer sheets"
                       hint="Drag & drop multiple files — image or PDF" />
          <Card.Body>
            <FileDropzone value={files} onChange={setFiles} multiple
                          accept="image/*,.pdf,application/pdf"
                          label="Drop one or many sheets here, or click to pick"
                          hint="JPG, PNG, WEBP or PDF (up to 16 pages per PDF). Up to 30 sheets per batch." />
            {isSingle && preview && <img className="preview" src={preview} alt="answer" />}
          </Card.Body>
        </Card>

        <div className="actions">
          <Button variant="primary" size="lg" loading={evalApi.loading} disabled={!canSubmit}
                  onClick={submit} icon="🔍">
            {evalApi.loading ? 'Evaluating…' : (files.length > 1 ? `Evaluate ${files.length} sheets` : 'Evaluate')}
          </Button>
          <span className="kbd-hint">⌘/Ctrl + ⏎ to submit</span>
        </div>

        {evalApi.loading && (
          <Card>
            <Card.Header eyebrow="Working" title="AI is reading the handwriting…"
                         hint={`${files.length} sheet${files.length > 1 ? 's' : ''} in flight — usually 5–15 seconds each`} />
            <Card.Body>
              <Skeleton h={70} count={Math.min(files.length || 1, 4)} />
            </Card.Body>
          </Card>
        )}

        {report && (
          <section className="bulk-results">
            <div className="results-head-row">
              <h3 className="results-h">
                📋 Results
                <span className="results-h-sub">
                  {report.graded}/{report.count} evaluated
                </span>
              </h3>
              {report.results.some(r => r.ok && r.transcript) && (
                <Button size="sm" icon="📥"
                        onClick={() => downloadAllTranscripts(report.results)}>
                  Download all transcripts (.txt)
                </Button>
              )}
            </div>

            <div className="result-cards">
              {report.results.map((r, i) => (
                <ResultCard
                  key={i}
                  result={r}
                  index={i}
                  isOpen={openIdx === i}
                  onToggle={() => setOpenIdx(openIdx === i ? -1 : i)}
                  showMarks={showMarks || hasAnyPdf}
                />
              ))}
            </div>
          </section>
        )}
      </main>

      <HistoryModal isOpen={histOpen} onClose={() => setHistOpen(false)}
                    onLoad={loadFromHistory}
                    accent="#10b981" accentDark="#06b6d4" />
    </div>
  )
}

function ResultCard({ result, index, isOpen, onToggle, showMarks }) {
  if (!result.ok) {
    return (
      <div className="rc rc-err">
        <div className="rc-head">
          <span className="rc-num">{index + 1}</span>
          <span className="rc-name">{result.file}</span>
          <span className="rc-err-txt">ERROR — {result.error}</span>
        </div>
      </div>
    )
  }

  const ds = result.detected_scope || {}
  const stars = result.handwriting_clarity ?? 0

  return (
    <div className={`rc ${isOpen ? 'rc-open' : ''}`}>
      <button className="rc-head rc-clickable" onClick={onToggle} aria-expanded={isOpen}>
        <span className="rc-num">{index + 1}</span>
        <span className="rc-name">{result.file}</span>
        <span className="rc-detected">
          G{ds.grade} · {ds.subject}{ds.chapter ? ` · ${ds.chapter}` : ''}
        </span>
        {showMarks && (
          <span className="rc-marks">{result.marks_awarded}/{result.marks_total}</span>
        )}
        {!result.is_typed && (
          <span className="rc-stars">{'★'.repeat(stars)}<span className="stars-faded">{'★'.repeat(5 - stars)}</span></span>
        )}
        {result.is_typed && <span className="rc-typed">⌨️ Typed</span>}
        <span className={`row-caret ${isOpen ? 'open' : ''}`}>▸</span>
      </button>

      {isOpen && (
        <div className="rc-body stagger-in">
          {/* 💪 Effort meter — shown alongside feedback so process is highlighted */}
          {typeof result.effort_score === 'number' && (
            <div className="effort-row">
              <div className="effort-label">💪 Effort score</div>
              <div className="effort-bar-bg">
                <div className="effort-bar-fill"
                     style={{ width: `${Math.max(0, Math.min(100, result.effort_score))}%` }} />
              </div>
              <div className="effort-pct">{result.effort_score}%</div>
            </div>
          )}

          {/* Feedback */}
          <div className="feedback-box">
            <div className="feedback-label">💬 Feedback for the student</div>
            <p>{result.feedback}</p>
          </div>

          {/* 📚 NCERT alignment — shows what NCERT says this chapter covers */}
          {result.ncert_alignment?.concepts && (
            <div className="ncert-block">
              <div className="ncert-head">
                📚 NCERT alignment — <b>{result.ncert_alignment.chapter}</b>
                <span className="ncert-meta">Grade {result.ncert_alignment.grade} · {result.ncert_alignment.subject}</span>
              </div>
              <div className="ncert-body">{result.ncert_alignment.concepts}</div>
            </div>
          )}

          {/* 🔧 Math verifier — only show when errors caught */}
          {result.math_check?.errors?.length > 0 && (
            <div className="mathcheck-block">
              <div className="mathcheck-head">🔧 Math verifier caught calculation error(s)</div>
              <ul>
                {result.math_check.errors.slice(0, 5).map((err, i) => (
                  <li key={i}>
                    <code>{err.expression}</code> — student wrote <b>{err.claimed}</b>,
                    actually <b>{err.correct}</b>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* First mistake */}
          {result.first_mistake && (
            <div className="first-mistake-card">
              <div className="fm-head">
                <span className="fm-pill">🎯 ROOT MISTAKE</span>
                <span className="fm-step">Step {result.first_mistake.step_index}</span>
              </div>
              <div className="fm-explain">
                This is the <b>first step where the student went wrong</b>. Every later step
                is affected — so the student loses marks for <i>this</i> mistake, not for downstream
                steps that only failed because of it.
              </div>
              <div className="fm-why"><b>Why it's wrong:</b> {result.first_mistake.why}</div>
              <div className="fm-fix"><b>How to fix it:</b> {result.first_mistake.correction}</div>
            </div>
          )}

          {/* Steps */}
          <h4 className="rc-steps-h">📋 Step-by-step</h4>
          <div className={`steps-list ${showMarks ? '' : 'no-marks'}`}>
            {(result.steps || []).map((s, i) => (
              <div key={i} className={`step step-${s.verdict} ${showMarks ? '' : 'step-no-marks'}`}>
                <div className="step-icon">{VERDICT_ICON[s.verdict] || '·'}</div>
                <div className="step-body">
                  <div className="step-text">{s.text}</div>
                  <div className="step-comment">{s.comment}</div>
                </div>
                {showMarks && (
                  <div className="step-marks">{s.marks_awarded}<span>/{s.marks_possible}</span></div>
                )}
              </div>
            ))}
          </div>

          <details className="rc-transcript-wrap">
            <summary>📝 Verbatim transcript</summary>
            <div className="transcript-toolbar">
              <Button size="sm" icon="⬇️"
                      onClick={() => downloadText(result.transcript || '', `${baseName(result)}_transcript.txt`)}>
                Download .txt
              </Button>
              <Button size="sm" icon="📋"
                      onClick={() => navigator.clipboard?.writeText(result.transcript || '')}>
                Copy
              </Button>
            </div>
            <pre className="transcript">{result.transcript}</pre>
          </details>
        </div>
      )}
    </div>
  )
}

function baseName(result) {
  const raw = result.detected_scope?.chapter || result.file || 'transcript'
  return String(raw).replace(/[^a-z0-9_-]/gi, '_').slice(0, 60)
}

function downloadText(text, filename) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function downloadAllTranscripts(results) {
  // Combine all transcripts into one file with separators
  const out = results
    .filter(r => r.ok && r.transcript)
    .map((r, i) => {
      const header = `═══════════════════════════════════════════\n` +
                     `Sheet ${i + 1}: ${r.file || 'untitled'}\n` +
                     `Detected: G${r.detected_scope?.grade} · ${r.detected_scope?.subject || ''}` +
                     (r.detected_scope?.chapter ? ` · ${r.detected_scope.chapter}` : '') + `\n` +
                     (typeof r.marks_awarded === 'number' ? `Marks: ${r.marks_awarded}/${r.marks_total}\n` : '') +
                     `═══════════════════════════════════════════\n\n`
      return header + r.transcript + '\n\n'
    })
    .join('')
  downloadText(out, 'all_transcripts.txt')
}
