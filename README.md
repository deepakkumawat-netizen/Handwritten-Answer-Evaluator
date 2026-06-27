# Handwritten Answer Evaluator

AI-powered handwritten answer sheet evaluator for CBSE schools. Upload scanned answer sheets (PDF/JPG/PNG), get step-by-step grading, handwriting clarity assessment, conceptual error detection, and NCERT-aligned feedback.

## Features

- **Step-by-step grading** — marks awarded per line of working, not just the final answer
- **Teacher Customization Panel** — set board, grade, subject, question-wise marks, grading rules, and feedback style
- **Grade-adaptive evaluation** — 5 grade tiers (1–2, 3–5, 6–8, 9–10, 11–12) with tier-appropriate strictness and vocab
- **Hard LLM constraints** — teacher's grading instructions become hard rules in the AI prompt
- **Handwriting clarity score** — 1–5 star rating with tone-appropriate feedback
- **First mistake detection** — identifies the exact step where the answer goes wrong
- **Effort score** — rewards correct process even when the final answer is wrong
- **Auto-detection** — AI infers grade, subject, and NCERT chapter from handwriting alone
- **NCERT alignment** — cross-references detected chapter to official curriculum
- **Math verifier** — sympy-based arithmetic validation catches calculation errors
- **Multi-language** — supports English and Hindi answers
- **Bulk evaluation** — up to 30 sheets in one request
- **Export** — PDF / DOCX transcripts with WYSIWYG editing

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18 + Vite, custom component library |
| Backend | FastAPI (Python), Uvicorn |
| Vision OCR | Gemini 2.5 Flash (primary), Groq Llama (fallback) |
| Image processing | pypdfium2 (PDF → PNG), Pillow |
| Math verification | sympy |
| Storage | SQLite (history, exam configs) |
| Ports | Backend: 8032 · Frontend: 5182 |

## Setup

### 1. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # add your API keys
uvicorn main:app --port 8032 --reload
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev                  # http://localhost:5182
```

### 3. Quick start (Windows)
```bash
start.bat
```

### Environment variables (`backend/.env`)
```
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key       # optional fallback
GEMINI_MODEL=gemini-2.5-flash
```

## How It Works

```
Teacher configures exam (grade, subject, marks per question, rules)
        ↓
Upload handwritten answer sheets (JPG / PNG / PDF)
        ↓
For each sheet:
  PDF → page images (pypdfium2)
  Images → Gemini Vision OCR + grading
  Step-by-step verdict per answer line
  Handwriting clarity scoring
  First mistake identification
  NCERT chapter alignment
  Math expression verification (sympy)
  Feedback polished for grade level
        ↓
Results: marks, step table, clarity stars,
         first mistake, effort score, NCERT ref
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/grade/handwriting` | Evaluate one or more answer sheets |
| GET/POST | `/api/exam-config` | List / save exam configurations |
| GET/DELETE | `/api/exam-config/{id}` | Fetch / delete one config |
| GET | `/api/health` | Service health check |
| GET | `/api/curriculum/{grade}` | Subjects and chapters for a grade |
| GET | `/api/history` | List past grading sessions |
| GET/DELETE | `/api/history/{id}` | Fetch / delete one session |
| POST | `/api/transcript/{fmt}` | Export transcript as PDF or DOCX |

## Project Structure

```
HandwritingEval/
├── backend/
│   ├── main.py                  # FastAPI app, all endpoints
│   ├── grading_prompts.py       # Step-by-step prompt + exam constraints
│   ├── llm_router.py            # Gemini/Groq calls + fallback chain
│   ├── grade_profiles.py        # GRADE_PROFILES + SUBJECT_GRADE_RULES
│   ├── exam_config_store.py     # SQLite CRUD for exam configs
│   ├── history_store.py         # Grading session history
│   ├── agent_tools.py           # Math verifier (sympy)
│   ├── cbse_kb.py               # CBSE curriculum knowledge base
│   ├── nlp_polish.py            # Feedback readability polish
│   ├── transcript_export.py     # PDF / DOCX export
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/Evaluator.jsx       # Main evaluation UI
│   │   ├── components/
│   │   │   ├── ExamConfigPanel.jsx   # Teacher customization panel
│   │   │   ├── EditorModal.jsx       # WYSIWYG transcript editor
│   │   │   └── HistoryModal.jsx      # Session history browser
│   │   └── styles/app.css
│   └── package.json
└── start.bat
```

---

Built for teachers at CBSE schools. Powered by [Codevidhya](https://codevidhya.com).
