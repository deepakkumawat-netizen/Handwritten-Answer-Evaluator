"""HandwritingEval — Handwritten answer step-by-step evaluator (Gemini Vision).

Supports image uploads (JPG, PNG, WEBP) and multi-page PDF uploads.
BULK MODE: multiple files in one request, each evaluated independently.
AI auto-detects grade/subject/chapter from each answer itself.
"""
from __future__ import annotations

import io
import os
import sys
import asyncio
from typing import Any

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fastapi.responses import StreamingResponse
from cbse_kb import get_subjects, get_chapters, retrieve_context
from grading_prompts import handwriting_prompt
from llm_router import grade_handwriting, QuotaExceeded
from nlp_polish import polish_feedback_dict
from agent_tools import verify_math
from transcript_export import transcripts_to_pdf, transcripts_to_docx
import history_store

import pypdfium2 as pdfium


app = FastAPI(title="HandwritingEval — Handwritten answer evaluator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5182", "http://127.0.0.1:5182"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "tool": "HandwritingEval",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    }


@app.get("/api/curriculum/{grade}")
def curriculum(grade: int):
    subjects = get_subjects(grade)
    return {"grade": grade, "subjects": {s: get_chapters(grade, s) for s in subjects}}


def _pdf_to_image_pages(raw: bytes, max_pages: int = 16, dpi: int = 150) -> list[tuple[bytes, str]]:
    pdf = pdfium.PdfDocument(raw)
    pages = []
    scale = dpi / 72
    for i, page in enumerate(pdf):
        if i >= max_pages: break
        bitmap = page.render(scale=scale)
        pil = bitmap.to_pil()
        buf = io.BytesIO()
        pil.save(buf, format="PNG", optimize=True)
        pages.append((buf.getvalue(), "image/png"))
    pdf.close()
    return pages


async def _evaluate_one(filename: str, raw: bytes, declared_mime: str,
                        question: str, max_marks: int) -> dict[str, Any]:
    """Evaluate a single answer (image or PDF) and return the result dict."""
    if not raw:
        return {"file": filename, "ok": False, "error": "empty file"}

    name = (filename or "").lower()
    is_pdf = declared_mime == "application/pdf" or name.endswith(".pdf") or raw[:4] == b"%PDF"

    try:
        if is_pdf:
            pages = await asyncio.to_thread(_pdf_to_image_pages, raw)
            if not pages:
                return {"file": filename, "ok": False, "error": "PDF has no readable pages"}
            images = pages
        else:
            mime = declared_mime or "image/jpeg"
            if not mime.startswith("image/"):
                mime = "image/jpeg"
            images = [(raw, mime)]
    except Exception as e:
        return {"file": filename, "ok": False, "error": f"Could not read file: {e}"}

    sys_prompt = handwriting_prompt(question, max_marks, pdf_mode=is_pdf)
    try:
        result = await asyncio.to_thread(grade_handwriting, sys_prompt, images)
    except QuotaExceeded as e:
        return {"file": filename, "ok": False, "error": str(e), "quota": True}
    except Exception as e:
        return {"file": filename, "ok": False, "error": f"Grading failed: {e}"}

    detected = result.get("detected_scope") or {}
    detected_grade = detected.get("grade") or 6

    # 📚 NCERT-grounding — cross-reference detected chapter to NCERT content
    try:
        ncert_ctx = retrieve_context(
            detected.get("chapter") or detected.get("subject", ""),
            detected_grade,
            detected.get("subject", ""),
            top_k=2,
        ) or ""
        if ncert_ctx:
            result["ncert_alignment"] = {
                "chapter":  detected.get("chapter"),
                "subject":  detected.get("subject"),
                "grade":    detected_grade,
                "concepts": ncert_ctx.strip()[:600],  # cap for UI display
            }
    except Exception:
        pass

    # 🔧 Math verifier — scan transcript for arithmetic errors
    try:
        transcript = result.get("transcript") or ""
        result["math_check"] = verify_math(transcript)
    except Exception:
        pass

    polish_feedback_dict(result, detected_grade)
    if is_pdf:
        result["source"] = {"type": "pdf", "pages": len(images)}
    return {"file": filename, "ok": True, **result}


@app.post("/api/grade/handwriting")
async def grade(
    question:  str  = Form(""),
    max_marks: int  = Form(5),
    image:     list[UploadFile] = File(...),
):
    """Evaluate one or many handwritten answers.
    `image` accepts a list of files (each evaluated independently).
    Each file may be JPG/PNG/WEBP or a PDF (up to 6 pages).
    """
    if not image:
        raise HTTPException(400, "No files uploaded")

    # Read all files first so async tasks can run concurrently
    payloads = []
    for f in image:
        raw = await f.read()
        payloads.append((f.filename or "untitled", raw, (f.content_type or "").lower()))

    # Gemini Vision is slower + rate-limited harder than text — cap at 3 concurrent
    sem = asyncio.Semaphore(3)
    async def bounded(payload):
        filename, raw, declared_mime = payload
        async with sem:
            return await _evaluate_one(filename, raw, declared_mime, question, max_marks)

    results = await asyncio.gather(*(bounded(p) for p in payloads))
    graded_count = sum(1 for r in results if r.get("ok"))

    # If every single file hit a quota error, surface as HTTP 429 so the UI can show a friendly message
    if results and not graded_count and all(r.get("quota") for r in results):
        raise HTTPException(429, results[0].get("error", "Gemini daily quota exhausted"))

    response = {
        "count": len(results),
        "graded": graded_count,
        "results": results,
    }

    # 🗂 Save to history (best-effort)
    try:
        graded = [r for r in results if r.get("ok")]
        subjects = sorted({(r.get("detected_scope") or {}).get("subject", "") for r in graded if r.get("detected_scope")})
        subjects_label = ", ".join(s for s in subjects if s)[:60] or "Mixed"
        title = f"{len(graded)} handwritten sheet{'s' if len(graded) != 1 else ''} — {subjects_label}"
        avg_clarity = (sum(r.get("handwriting_clarity", 0) for r in graded) / len(graded)) if graded else 0
        summary = f"Avg handwriting clarity: {avg_clarity:.1f}/5 · {len(graded)}/{len(results)} graded"
        hid = await asyncio.to_thread(history_store.save_history, title, summary, question or "", response)
        response["history_id"] = hid
    except Exception as e:
        print(f"[history] save failed: {e}")

    return JSONResponse(response)


# ─── History (SQLite) ───────────────────────────────────────────────────────
@app.get("/api/history")
def history_list():
    return {"items": history_store.list_history(limit=50)}


@app.get("/api/history/{hid}")
def history_get(hid: int):
    h = history_store.get_history(hid)
    if not h:
        raise HTTPException(404, "Not found")
    return h


@app.delete("/api/history/{hid}")
def history_delete(hid: int):
    history_store.delete_history(hid)
    return {"ok": True}


@app.delete("/api/history")
def history_clear():
    history_store.clear_history()
    return {"ok": True}


# ─── Transcript export (PDF / DOCX) ─────────────────────────────────────────
@app.post("/api/transcript/{fmt}")
async def transcript_export(fmt: str, payload: dict):
    fmt = (fmt or "").lower()
    if fmt not in {"pdf", "docx"}:
        raise HTTPException(400, "Format must be pdf or docx")
    items = payload.get("items") or []
    if not items:
        raise HTTPException(400, "No items")
    filename = payload.get("filename") or f"transcripts.{fmt}"
    if fmt == "pdf":
        blob = await asyncio.to_thread(transcripts_to_pdf, items)
        mime = "application/pdf"
    else:
        blob = await asyncio.to_thread(transcripts_to_docx, items)
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return StreamingResponse(iter([blob]), media_type=mime,
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
