"""
Invoice upload & extraction router.

POST /invoice/upload
  – Accepts a PDF invoice file, extracts all customs-relevant fields via
    OpenAI, and returns structured JSON ready for the duty calculator.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.responses import ok
from app.engines.base import EngineError
from app.engines.invoice_extraction import extract_invoice_fields

router = APIRouter()

_MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/upload",
    summary="Upload a PDF invoice and extract fields for the duty calculator",
    response_description="Structured invoice fields extracted by AI",
)
async def upload_invoice(
    file: UploadFile = File(..., description="Commercial invoice in PDF format"),
):
    """
    Upload a commercial invoice PDF.

    The endpoint:
    1. Validates the file is a PDF (content-type + magic bytes).
    2. Extracts embedded text with **pypdf**.
    3. Sends the text to **OpenAI** (gpt-4o by default) for structured field
       extraction — seller, buyer, line items, HS codes, totals, incoterms, etc.
    4. Returns a JSON payload that can be fed directly into the duty calculator.

    **Scanned / image-based PDFs**: text extraction will be sparse and the AI
    will flag a warning in the response; results may be incomplete.
    """
    # ── 1. Validate content type ──────────────────────────────────────────
    content_type = file.content_type or ""
    if content_type not in ("application/pdf", "application/octet-stream", ""):
        # Browsers sometimes send octet-stream; we do a magic-byte check below.
        if "pdf" not in content_type.lower():
            raise HTTPException(
                status_code=415,
                detail="Only PDF files are accepted (content-type must be application/pdf).",
            )

    # ── 2. Read bytes ─────────────────────────────────────────────────────
    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(pdf_bytes) > _MAX_PDF_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {_MAX_PDF_BYTES // (1024 * 1024)} MB.",
        )

    # ── 3. Magic-byte check (PDF starts with %PDF) ────────────────────────
    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=415,
            detail="Uploaded file does not appear to be a valid PDF.",
        )

    # ── 4. Extract fields via engine ──────────────────────────────────────
    try:
        result = extract_invoice_fields(
            pdf_bytes=pdf_bytes,
            filename=file.filename or "invoice.pdf",
        )
    except EngineError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": exc.message})

    return ok(result)
