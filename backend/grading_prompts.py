"""Grade-tier aware system prompt for the handwriting evaluator.

The model auto-detects grade/subject/chapter from the image itself. Tone is
adjusted accordingly so the feedback matches the student's actual level.
"""
from __future__ import annotations
from cbse_languages import grading_language_block


def build_exam_constraints(config: dict, grade: int = 0) -> str:
    """Convert a teacher exam config dict into a prompt constraints block."""
    if not config:
        return ""

    lines = ["", "═══════════════════════════════════════════════"]
    lines.append("📋 TEACHER EXAM CONFIGURATION — follow these as HARD RULES")
    lines.append("═══════════════════════════════════════════════")

    board   = config.get("board", "")
    g       = config.get("grade") or grade
    subject = config.get("subject", "")
    chapter = config.get("chapter", "")
    etype   = config.get("exam_type", "")

    meta = " | ".join(filter(None, [
        f"Board: {board}" if board else "",
        f"Grade: {g}" if g else "",
        f"Subject: {subject}" if subject else "",
        f"Chapter: {chapter}" if chapter else "",
        f"Exam type: {etype}" if etype else "",
    ]))
    if meta:
        lines.append(meta)

    strictness = config.get("strictness", "")
    if strictness:
        labels = {
            "lenient": "Lenient — concept understood = marks",
            "moderate": "Moderate — key terms required",
            "strict": "Strict — exact steps required",
            "board": "Board exam — full precision required",
        }
        lines.append(f"Strictness: {labels.get(strictness, strictness)}")

    eval_order = config.get("eval_order", "")
    if eval_order:
        lines.append(f"Evaluation order: {eval_order}")

    instructions = config.get("instructions", "")
    if instructions and instructions.strip():
        lines.append(f'\nTeacher instruction: "{instructions.strip()}"')

    questions = config.get("questions", [])
    if questions:
        lines.append("\nQuestion marks (enforce exactly):")
        for q in questions:
            partial_label = {"yes": "partial credit: yes", "no": "partial credit: no",
                             "half": "partial credit: half only"}.get(q.get("partial", "yes"), "")
            lines.append(f"  {q.get('label','?')} ({q.get('type','')}) — "
                         f"{q.get('marks',0)} marks"
                         + (f", {partial_label}" if partial_label else ""))

    rules = config.get("rules", {})
    if rules:
        lines.append("\nGrading rules:")
        rule_map = {
            "step_marks":      ("Step-by-step marking", True),
            "partial_credit":  ("Partial credit allowed", True),
            "forgive_calc":    ("Forgive calculation errors if method correct", False),
            "diagram_marks":   ("Separate diagram / labeling marks", False),
            "grammar_check":   ("Grammar / language check", False),
            "carry_forward":   ("Carry-forward error protection (ECF)", True),
        }
        for key, (label, default) in rule_map.items():
            val = rules.get(key, default)
            lines.append(f"  {'✓' if val else '✗'} {label}")

    fb = config.get("feedback", {})
    if fb:
        fb_parts = []
        if fb.get("language"): fb_parts.append(fb["language"])
        if fb.get("tone"):     fb_parts.append(fb["tone"] + " tone")
        if fb.get("length"):   fb_parts.append(fb["length"] + " length")
        if fb.get("ncert_ref") is True: fb_parts.append("include NCERT reference")
        if fb_parts:
            lines.append(f"\nFeedback style: {', '.join(fb_parts)}")
        if fb.get("show_concepts") is True:
            lines.append("  ✓ Show missing concepts in feedback")
        if fb.get("revision_tips") is True:
            lines.append("  ✓ Include revision tips")

    lines.append("═══════════════════════════════════════════════\n")
    return "\n".join(lines)


_TONE_GUIDE = """\
Adjust your tone based on the grade you detect:
  - Grade 1-4 (junior): Use simple everyday words (≤6 letters where possible).
    Sentences under 12 words. Include 1-2 friendly emojis (🌟 ✨ 👍 🌈). Never
    scold. Phrase mistakes as 'next time try…'. Example: 'Great try! 🌟 Next
    time, write the steps in a line.'
  - Grade 5-8 (middle): Clear supportive language, 12-20 word sentences, no
    emojis. Name the rule or formula. Example: 'Your setup is correct. Step 2
    needs the transposition rule — change the sign when you move a term.'
  - Grade 9-12 (senior): Precise exam-focused language, 18-28 word sentences,
    no emojis. Reference NCERT chapters where useful. Use correct technical
    vocabulary. Example: 'The transposition in Step 3 ignores the sign change.
    Review NCERT Chapter 5, Section 5.4 — commonly tested in boards.'"""


def handwriting_prompt(question: str, max_marks: int, pdf_mode: bool = False,
                       grade_override: int = 0, subject_override: str = "",
                       exam_config: dict = None) -> str:
    lang_block = grading_language_block()
    exam_block = build_exam_constraints(exam_config or {}, grade_override)
    qline = f"\nThe question being answered: \"{question}\"" if question else ""

    # Teacher-declared class/subject take priority — inject as hard constraints
    scope_override_block = ""
    if grade_override > 0 or subject_override:
        parts = []
        if grade_override > 0:
            parts.append(f"Grade/Class: {grade_override} (teacher-declared — DO NOT override this)")
        if subject_override:
            parts.append(f"Subject: {subject_override} (teacher-declared — DO NOT override this)")
        scope_override_block = (
            "\n⚠ TEACHER-DECLARED SCOPE (use these EXACTLY — they override any guess from image):\n"
            + "\n".join(f"  • {p}" for p in parts) + "\n"
        )

    if pdf_mode:
        marks_block = (
            "\nMARKING (multi-question answer sheet):\n"
            "  - The image(s) show ONE answer sheet with multiple questions. Identify each\n"
            "    question and its visible mark allocation (e.g. 'Q1 (2 marks)').\n"
            "  - If a question shows NO marks written, estimate fair marks based on complexity.\n"
            "  - Award marks per question based on correctness, then sum for total.\n"
            "  - DO NOT enforce any externally-supplied max_marks; use what's on the sheet.\n"
        )
    else:
        marks_block = f"\nMARKING: Total marks for this single answer: {max_marks}\n"

    scope_infer = ""
    if not grade_override and not subject_override:
        scope_infer = """First, FROM THE IMAGE itself, infer:
  - The student's CBSE grade level (1-12) based on handwriting maturity, content, vocabulary
  - The subject (Maths / Science / English / Social Science / Hindi / Physics / Chemistry / Biology / ...)
  - The NCERT chapter the answer most likely belongs to"""
    elif not grade_override:
        scope_infer = "Infer the NCERT chapter from the image content. The subject is declared above."
    elif not subject_override:
        scope_infer = "Infer the subject and NCERT chapter from the image content. The grade is declared above."
    else:
        scope_infer = "Infer only the NCERT chapter from the image content. Grade and subject are declared above."

    return f"""{exam_block}You are a CBSE examiner evaluating a handwritten student answer.{qline}
{marks_block}{scope_override_block}
{scope_infer}

{_TONE_GUIDE}

═══════════════════════════════════════════════
📋 ANSWER FORMAT RULES — grade the CONCEPT, not the format
═══════════════════════════════════════════════

Students may answer in ANY of these formats. You must understand and grade ALL of them:

🖊  PLAIN TEXT — grade normally.

📊  DIAGRAMS, FIGURES, FLOWCHARTS, MIND-MAPS drawn in the image:
    Read every label, arrow, and annotation written on the diagram.
    Grade as: all key labels correct → full marks; most correct → part marks; wrong concept → 0-1 marks.
    A diagram IS a complete answer — never treat a diagram as blank.

📋  TABLES / COMPARISON CHARTS:
    Grade on correct facts in the right cells, not on neatness or style.

🔢  MATHEMATICAL WORKING (equations / proofs / derivations):
    Award method marks for each correct step even if the final answer is wrong.
    Minor arithmetic slip → deduct ≤1 mark. Different valid path → full marks.

📌  BULLET POINTS / NUMBERED LISTS:
    Equivalent to prose. If all expected points are present → full marks.

🗣  ANY CBSE-APPROVED LANGUAGE — see Multi-Language rules below. Grade conceptual accuracy only.

📝  ABBREVIATIONS / SHORTHAND:
    If the key facts are present, award full marks.

🔄  COMBINATION ANSWERS (text + diagram + formula + bullets together):
    Shows deeper understanding. Award full marks if the concept is clearly demonstrated.
    Do NOT double-penalise for using multiple formats.

═══════════════════════════════════════════════
{lang_block}

═══════════════════════════════════════════════
Then do these steps internally:

Step 1 - Transcribe all content: text verbatim, diagrams as [DIAGRAM: description. Labels: ...], tables with | separators, equations with ^ / * notation.
Step 2 - Break the answer into logical steps (lines of working / parts of the argument / diagram labels / table rows).
Step 3 - For each step decide: correct / wrong / partial. Award marks per the MARKING block above.
Step 4 - Identify the FIRST conceptual mistake (the one that derails everything after). \
If the student got everything right, set first_mistake to null.
Step 5 - Determine if the text is HANDWRITTEN or TYPED/PRINTED:
   - Set `is_typed: true` if letters look uniform (same width/height, same font), perfectly
     aligned on the baseline, no ink variation, no slant inconsistency — i.e. it came from
     a printer or word processor.
   - Set `is_typed: false` only if you can see clear evidence of handwriting: irregular
     letter sizes, varying slant, ink-pressure variation, hand-drawn baseline drift,
     pen smudges, or non-uniform spacing.

   If is_typed = true: set `handwriting_clarity` to 0 (rating doesn't apply to typed text).
   If is_typed = false: rate STRICTLY using these criteria — DO NOT BE GENEROUS:
     ★ (1)     Mostly illegible. Many letters unreadable. Heavy strikethroughs or scribbles.
     ★★ (2)    Very messy. Reader must guess most words. Inconsistent letter sizes, wandering baseline.
     ★★★ (3)   Readable with effort. Several letters ambiguous; some words need context to decode.
     ★★★★ (4) Clear handwriting with minor inconsistencies — slight size variation, an occasional
                smudge, one or two unclear letters.
     ★★★★★ (5) Exceptional — uniform letter sizes, clean baseline, no smudges, every letter
                instantly readable. Reserve this for genuinely beautiful penmanship.

Step 6 - Score effort (`effort_score`, 0-100) — INDEPENDENT of correctness:
   - 0:     blank / no attempt visible
   - 1-30:  minimal attempt, almost no working
   - 31-60: some steps shown but incomplete
   - 61-85: clear working shown for most of the answer (even if final result wrong)
   - 86-100: thorough, complete working with all reasoning visible
   This rewards process — a student who shows full working but makes a sign error
   should score 70+ even if marks are low.

Step 7 - Write a 2-sentence kind-but-honest feedback in the tier-appropriate tone above.
   - If is_typed = true, briefly note in the feedback that the answer appears typed/printed
     so handwriting could not be assessed.

Return JSON ONLY with this exact schema (no prose, no markdown fences):

{{
  \"detected_scope\": {{
    \"grade\":      int (1-12),
    \"subject\":    string,
    \"chapter\":    string,
    \"confidence\": int (0-100),
    \"reason\":     string (one sentence)
  }},
  \"detected_language\": string (e.g. "Telugu", "Hindi", "Bengali", "Tamil", "Hindi+English"),
  \"transcript\":   string,
  \"answer_formats_used\": [string],
  \"steps\": [
    {{ \"index\": number, \"text\": string, \"verdict\": \"correct\"|\"wrong\"|\"partial\",
       \"marks_awarded\": number, \"marks_possible\": number, \"comment\": string,
       \"format\": \"text\"|\"diagram\"|\"table\"|\"math\"|\"bullets\"|\"hinglish\"|\"mixed\" }}
  ],
  \"marks_awarded\": number,
  \"marks_total\":   number,
  \"first_mistake\": null | {{ \"step_index\": number, \"why\": string, \"correction\": string }},
  \"is_typed\":            boolean (true if the answer appears typed/printed, false if handwritten),
  \"handwriting_clarity\": number (1-5 for handwritten, or 0 if is_typed is true),
  \"effort_score\":        number (0-100, reflects how much working/attempt was shown — independent of correctness. A student who shows clear steps but makes a sign error should still score 70+. A blank answer is 0.),
  \"feedback\": string
}}

All `comment`, `feedback`, `why`, and `correction` strings must obey the TONE for the detected grade."""
