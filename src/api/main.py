"""
src/api/main.py

MedSight FastAPI backend.
Orchestrates the full pipeline:
  upload → ingest → NER → flag → history → LLM → response
"""

import os
import uuid
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.ingestion.document_loader import load_document, chunk_text
from src.ner.medical_ner import extract_entities, merge_chunk_entities
from src.flagging.risk_flagging import flag_lab_values, flag_trends, compute_risk_summary
from src.history.patient_history import (
    store_report,
    get_patient_history,
    get_historical_lab_values,
    list_patients,
    delete_patient,
)
from src.llm.summarizer import run_full_analysis

app = FastAPI(
    title="MedSight API",
    description="Offline Clinical Intelligence Platform for Indian Healthcare",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory report cache for the session
_report_cache: dict[str, dict] = {}


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "MedSight"}


# ── Debug ─────────────────────────────────────────────────────────────────────

@app.post("/debug/extract")
async def debug_extract(file: UploadFile = File(...)):
    """
    Debug endpoint — runs ingestion + NER only.
    Returns raw extracted text and lab values so we can verify
    the pipeline is parsing correctly before full analysis.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        doc = load_document(tmp_path)
        raw_text = doc["raw_text"]
        chunks = chunk_text(raw_text, chunk_size=400, overlap=50)
        chunk_entities = [extract_entities(chunk) for chunk in chunks[:8]]
        entities = merge_chunk_entities(chunk_entities)
        return {
            "raw_text": raw_text,
            "lab_values": entities["lab_values"],
            "patient": entities["patient"],
            "diagnoses": entities["clinical"]["diagnoses"],
        }
    finally:
        os.unlink(tmp_path)


# ── Report Processing ─────────────────────────────────────────────────────────

@app.post("/report/upload")
async def upload_report(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    report_date: str = Form(default=""),
):
    """
    Upload and process a medical report PDF.
    Runs full pipeline: ingest → NER → flag → history → LLM.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Save upload to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # ── Step 1: Ingest ────────────────────────────────────────────────
        doc = load_document(tmp_path)
        raw_text = doc["raw_text"]

        # ── Step 2: NER ───────────────────────────────────────────────────
        chunks = chunk_text(raw_text, chunk_size=400, overlap=50)
        chunk_entities = [extract_entities(chunk) for chunk in chunks[:8]]  # cap at 8 chunks
        entities = merge_chunk_entities(chunk_entities)

        # ── Step 3: Rule-based flagging ───────────────────────────────────
        gender = entities.get("patient", {}).get("gender")
        rule_flags = flag_lab_values(entities["lab_values"], gender=gender)

        # ── Step 4: Trend flagging (longitudinal) ─────────────────────────
        historical_labs = get_historical_lab_values(patient_id)
        print(f"[DEBUG] Patient {patient_id}: {len(historical_labs)} historical reports found")
        for i, hl in enumerate(historical_labs):
            print(f"[DEBUG] Historical report {i+1}: {hl}")
        trend_flags = flag_trends(
            current_labs=entities["lab_values"],
            historical_labs=historical_labs,
        )

        # ── Step 5: Risk summary ──────────────────────────────────────────
        risk_summary = compute_risk_summary(rule_flags, trend_flags)

        # ── Step 6: LLM analysis ──────────────────────────────────────────
        llm_output = run_full_analysis(
            entities=entities,
            flags=rule_flags,
            trend_flags=trend_flags,
            raw_text_snippet=raw_text[:1000],
        )

        # ── Step 7: Store in history ──────────────────────────────────────
        # Sanitize date — strip time component if present
        clean_date = None
        if report_date:
            clean_date = str(report_date).split(" ")[0].split("T")[0]

        report_id = store_report(
            patient_id=patient_id,
            report_text=raw_text,
            entities=entities,
            flags=rule_flags,
            lab_values=entities["lab_values"],
            report_date=clean_date,
            filename=file.filename,
        )

        # ── Build response ────────────────────────────────────────────────
        result = {
            "report_id": report_id,
            "patient_id": patient_id,
            "filename": file.filename,
            "source_type": doc["source_type"],
            "has_hindi": doc["has_hindi"],
            "pages": doc["pages"],
            "entities": entities,
            "rule_flags": [
                {**f, "severity": str(f["severity"])} for f in rule_flags
            ],
            "trend_flags": [
                {**f, "severity": str(f["severity"])} for f in trend_flags
            ],
            "risk_summary": {
                **risk_summary,
                "overall_severity": str(risk_summary["overall_severity"]),
            },
            "llm_output": llm_output,
        }

        # Cache for quick retrieval
        _report_cache[report_id] = result
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


@app.get("/report/{report_id}")
def get_report(report_id: str):
    """Retrieve a cached processed report by ID."""
    if report_id not in _report_cache:
        raise HTTPException(status_code=404, detail="Report not found in session cache.")
    return _report_cache[report_id]


# ── Patient History ───────────────────────────────────────────────────────────

@app.get("/patient/{patient_id}/history")
def patient_history(patient_id: str):
    """Get all stored reports for a patient."""
    history = get_patient_history(patient_id)
    return {"patient_id": patient_id, "report_count": len(history), "reports": history}


@app.get("/patients")
def all_patients():
    """List all patient IDs in the system."""
    return {"patients": list_patients()}


@app.delete("/patient/{patient_id}")
def remove_patient(patient_id: str):
    """Delete all data for a patient."""
    success = delete_patient(patient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return {"message": f"Patient {patient_id} deleted successfully."}
