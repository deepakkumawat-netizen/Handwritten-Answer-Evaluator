/**
 * Marks selector — horizontal range slider PLUS a number input that share state.
 * Range 1-100. Either control updates the value.
 */
export default function MarksSlider({ value, onChange, disabled, min = 1, max = 100 }) {
  const clamp = (v) => Math.max(min, Math.min(max, v))

  const onRange = (e) => onChange(Number(e.target.value))
  const onNum   = (e) => {
    const v = Number(e.target.value)
    if (Number.isNaN(v)) return
    onChange(clamp(v))
  }

  return (
    <div className="marks-slider">
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={onRange}
        disabled={disabled}
        className="ms-range"
        aria-label="Max marks slider"
      />
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={onNum}
        disabled={disabled}
        className="ms-num"
        aria-label="Max marks number"
      />
      <div className="ms-ticks" aria-hidden>
        <span>1</span><span>25</span><span>50</span><span>75</span><span>100</span>
      </div>
    </div>
  )
}
