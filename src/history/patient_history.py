"""
src/history/patient_history.py

Longitudinal patient history store using ChromaDB.
Stores report embeddings and lab values per patient.
Enables trend analysis across multiple visits.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Persistent ChromaDB storage
DB_PATH = Path(__file__).parent.parent.parent / "data" / "patient_history_db"
DB_PATH.mkdir(parents=True, exist_ok=True)

_client = None
_embedder = None


def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(DB_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def _get_embedder():
    global _embedder
    if _embedder is None:
        # Lightweight model — runs on CPU fine
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _get_collection(patient_id: str):
    """Get or create a ChromaDB collection per patient."""
    client = _get_client()
    # Collection names must be alphanumeric + hyphens
    safe_id = "patient-" + "".join(c if c.isalnum() else "-" for c in patient_id)
    return client.get_or_create_collection(
        name=safe_id,
        metadata={"hnsw:space": "cosine"},
    )


def store_report(
    patient_id: str,
    report_text: str,
    entities: dict,
    flags: list[dict],
    lab_values: list[dict],
    report_date: str = None,
    filename: str = "",
) -> str:
    """
    Store a processed report in ChromaDB for a patient.

    Returns:
        report_id (str)
    """
    collection = _get_collection(patient_id)
    embedder = _get_embedder()

    report_id = str(uuid.uuid4())
    date_str = report_date or datetime.now().strftime("%Y-%m-%d")

    # Embed the report text (first 512 words)
    short_text = " ".join(report_text.split()[:512])
    embedding = embedder.encode(short_text).tolist()

    # Store metadata as JSON strings (ChromaDB only supports string metadata)
    metadata = {
        "patient_id": patient_id,
        "report_date": date_str,
        "filename": filename,
        "lab_values_json": json.dumps(lab_values),
        "flags_json": json.dumps(
            [{**f, "severity": str(f["severity"])} for f in flags]
        ),
        "diagnoses_json": json.dumps(
            entities.get("clinical", {}).get("diagnoses", [])
        ),
        "medications_json": json.dumps(entities.get("medications", [])),
    }

    collection.add(
        ids=[report_id],
        embeddings=[embedding],
        documents=[short_text],
        metadatas=[metadata],
    )

    return report_id


def get_patient_history(patient_id: str) -> list[dict]:
    """
    Retrieve all stored reports for a patient, sorted oldest first.

    Returns:
        list of {
            report_id, report_date, filename,
            lab_values, flags, diagnoses, medications
        }
    """
    try:
        collection = _get_collection(patient_id)
        results = collection.get(include=["metadatas", "documents"])
    except Exception:
        return []

    if not results or not results["ids"]:
        return []

    reports = []
    for i, report_id in enumerate(results["ids"]):
        meta = results["metadatas"][i]
        reports.append({
            "report_id": report_id,
            "report_date": meta.get("report_date", ""),
            "filename": meta.get("filename", ""),
            "lab_values": json.loads(meta.get("lab_values_json", "[]")),
            "flags": json.loads(meta.get("flags_json", "[]")),
            "diagnoses": json.loads(meta.get("diagnoses_json", "[]")),
            "medications": json.loads(meta.get("medications_json", "[]")),
        })

    # Sort by date ascending (oldest first)
    reports.sort(key=lambda r: r["report_date"])
    return reports


def get_historical_lab_values(patient_id: str) -> list[list[dict]]:
    """
    Return lab values from all past reports for trend analysis.
    Each inner list is one report's lab values, oldest first.
    """
    history = get_patient_history(patient_id)
    return [r["lab_values"] for r in history]


def get_similar_reports(
    patient_id: str,
    query_text: str,
    n_results: int = 3,
) -> list[dict]:
    """
    Semantic search over a patient's report history.
    Useful for finding past reports with similar clinical context.
    """
    try:
        collection = _get_collection(patient_id)
        embedder = _get_embedder()
        query_embedding = embedder.encode(query_text).tolist()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            include=["metadatas", "documents", "distances"],
        )
    except Exception:
        return []

    similar = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        similar.append({
            "report_id": results["ids"][0][i],
            "report_date": meta.get("report_date", ""),
            "filename": meta.get("filename", ""),
            "similarity_score": round(1 - results["distances"][0][i], 3),
            "diagnoses": json.loads(meta.get("diagnoses_json", "[]")),
        })
    return similar


def list_patients() -> list[str]:
    """Return all patient IDs currently stored."""
    client = _get_client()
    collections = client.list_collections()
    return [
        c.name.replace("patient-", "")
        for c in collections
        if c.name.startswith("patient-")
    ]


def delete_patient(patient_id: str) -> bool:
    """Delete all stored data for a patient."""
    try:
        client = _get_client()
        safe_id = "patient-" + "".join(
            c if c.isalnum() else "-" for c in patient_id
        )
        client.delete_collection(safe_id)
        return True
    except Exception:
        return False
