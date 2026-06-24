"""Local Grading & OCR Engine — uses Microsoft Florence-2 for handwriting OCR
and OpenCV for OMR (bubble-sheet) grading. Runs fully local, no external API.

Endpoints:
  POST /api/v1/grade-omr            — OMR bubble-sheet grading
  POST /api/v1/evaluate-handwriting — Florence-2 handwritten OCR
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
import cv2
import numpy as np
from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
import io

app = FastAPI(title="Local Grading & OCR Engine")

# --- 1. Load Handwriting Model at Startup ---
print("Loading Florence-2 model... (This takes a moment)")
model_id = "microsoft/Florence-2-large"
processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
print("Model loaded successfully!")

# --- 2. OMR Processing Function ---
def process_omr(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

    if img is None:
        raise ValueError("Invalid image file")

    _, thresh = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY_INV)

    # NOTE: In production, slice 'thresh' using exact coordinates from your
    # exam-sheet template (e.g. bubble_roi = thresh[y1:y2, x1:x2]).
    total_pixels = thresh.shape[0] * thresh.shape[1]
    filled_pixels = cv2.countNonZero(thresh)
    fill_ratio = filled_pixels / total_pixels

    is_filled = fill_ratio > 0.3  # 30% threshold for a filled bubble

    return {"status": "success", "fill_ratio": fill_ratio, "is_filled": bool(is_filled)}


# --- Endpoints ---

@app.post("/api/v1/grade-omr")
async def grade_omr_endpoint(file: UploadFile = File(...)):
    """Endpoint for structured auto-grading (bubbles, checkboxes)"""
    try:
        contents = await file.read()
        result = process_omr(contents)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/evaluate-handwriting")
async def evaluate_handwriting_endpoint(file: UploadFile = File(...)):
    """Endpoint for extracting handwritten text using Florence-2"""
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        prompt = "<OCR>"
        inputs = processor(text=prompt, images=image, return_tensors="pt")

        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
        )

        extracted_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        extracted_text = extracted_text.replace("<OCR>", "").strip()

        return {"status": "success", "extracted_text": extracted_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
