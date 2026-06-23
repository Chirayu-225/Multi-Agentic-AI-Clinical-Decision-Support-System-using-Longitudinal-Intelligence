# Offline Multi-Agent Clinical Decision Support System

> A privacy-preserving, offline multi-agent AI system that extracts clinical entities from medical reports, flags risk against Indian (ICMR) reference ranges, tracks patient trends across visits, and self-verifies its own generated output before delivery.

---

## What it is

- **Type:** Multi-agent AI system (2 agents) — not a simple LLM wrapper, not a single-shot prompt pipeline
- **Agent 1 — Generation Agent:** extracts entities, applies risk rules, generates clinical and patient-facing summaries
- **Agent 2 — Verification Agent:** audits Agent 1's output against the actual extracted data, rejects and corrects any unsupported/hallucinated claim before it reaches the user
- **Both agents share one loaded local LLM instance** (different system prompts, same model) — keeps the whole system inside 4GB VRAM
- **Fully offline:** no API calls, no cloud inference, at any stage

---

## Why a multi-agent design

- During testing, the generation agent occasionally fabricated values not present in the source report (e.g. cholesterol, blood pressure, HbA1c when none were tested)
- Rather than just improving prompts, a second agent was added with one job: read the draft output, compare it line-by-line against ground-truth extracted data, and force a rewrite if anything doesn't check out
- This is the standard agent-handoff pattern (generate → verify → correct), scoped down to something that actually fits a single consumer GPU

---

## The Problem

Clinicians in under-resourced Indian hospitals and clinics spend significant time manually reviewing complex lab reports and discharge summaries. Specialist access is limited. Patients often can't understand their own reports. Single-visit analysis misses worsening trends that only become visible over time. And AI-generated medical summaries carry a real risk of hallucinating values that were never actually in the report — a risk this system is explicitly designed to catch.

---

## Core pipeline (what happens to a report)

1. **Ingest** — digital PDFs parsed directly; scanned/handwritten PDFs run through OCR; Hindi text auto-detected and transliterated
2. **Extract** — named entity recognition pulls patient info, diagnoses, medications, lab values from unstructured text
3. **Flag (rule-based)** — every lab value checked against ICMR Indian reference ranges, not Western defaults; severity levels: Normal / Moderate / High / Critical
4. **Flag (trend-based)** — patient's historical values pulled from vector store; consistent multi-visit directional trends flagged even when no single reading is severe alone
5. **Generate** — Agent 1 produces a clinical summary, a patient-friendly summary, per-flag explanations, and follow-up actions
6. **Verify** — Agent 2 checks both summaries against ground truth; corrects and re-verifies if unsupported claims are found
7. **Deliver** — final, verified output shown with a visible badge: verified clean, or verified-and-corrected

---

## Novelty, in short

- Multi-agent self-verification — a generation agent and a verification agent that actually catches hallucination, demonstrated in testing
- Fully offline, two-agent architecture inside 4GB VRAM — no cloud, no second model load
- Longitudinal trend intelligence — trends across visits, not single-report snapshots
- ICMR-grounded, not Western-default, risk thresholds
- Every flag and every correction is explainable — traceable to a specific value, guideline, or ground-truth mismatch

---

## Tech Stack

| Layer | Technology |
|---|---|
| Document ingestion | PyMuPDF, EasyOCR |
| Language handling | langdetect, indic-transliteration |
| Medical NER | GLiNER (urchade/gliner_mediumv2.1) + custom rule-based lab-value parser |
| Patient history | ChromaDB + sentence-transformers |
| Risk flagging | Rule-based (ICMR JSON) + trend analysis |
| Generation agent | Phi-3 Mini 4-bit (llama-cpp-python) |
| Verification agent | Phi-3 Mini 4-bit, same instance, distinct role/prompt |
| API | FastAPI |
| Frontend | Streamlit + Plotly |
| Deployment | Docker + Docker Compose |

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/yourusername/medsight.git
cd medsight
pip install -r requirements.txt
```

### 2. Download the model

Download **Phi-3-mini-4k-instruct-q4.gguf** from:
https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf

Place it at:
```
models/phi-3-mini-4k-instruct-q4.gguf
```

### 3. Run locally (without Docker)

Terminal 1 — API:
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2 — Frontend:
```bash
streamlit run app/streamlit_app.py
```

Open: http://localhost:8501

### 4. Run with Docker

```bash
docker-compose up --build
```

Open: http://localhost:8501

---

## Data Sources Used for Testing

- **MTSamples** (mtsamples.com) — free de-identified medical transcripts
- **Synthea** — synthetic patient record generator
- **PhysioNet** — open clinical datasets

---

## Project Structure

```
medsight/
├── src/
│   ├── ingestion/       # PDF loading, OCR, Hindi transliteration
│   ├── ner/             # GLiNER medical entity extraction
│   ├── flagging/        # ICMR rule-based + trend risk flagging
│   ├── llm/             # Phi-3 Mini summarization + explainability
│   ├── history/         # ChromaDB longitudinal patient store
│   └── api/             # FastAPI endpoints
├── app/
│   └── streamlit_app.py # Frontend UI
├── data/
│   ├── patient_history_db/   # ChromaDB persistent store
│   └── sample_reports/       # Test PDFs
├── models/              # Local GGUF model files
├── tests/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## GPU Requirements

Tested on RTX 3050 Ti (4GB VRAM). Phi-3 Mini 4-bit uses ~2.5GB VRAM.
If you encounter VRAM issues, reduce `n_gpu_layers` in `src/llm/summarizer.py`.

---

## Impact

Built for the Indian healthcare context where:
- Rural clinics lack specialist access
- Telemedicine platforms need automated report triage
- Patients often receive complex reports with no explanation
- Data privacy regulations prevent cloud-based processing of PHI


## Project Snippets 

1) Main Page

<img width="1591" height="784" alt="image" src="https://github.com/user-attachments/assets/b170e569-9eee-45c3-a55a-3671d5552c3a" />


2) Multi-Report Analysis with Agentic Reasoning

<img width="1563" height="748" alt="image" src="https://github.com/user-attachments/assets/715ed829-3551-4359-bdce-fbc6f2c165da" />

<img width="1518" height="891" alt="image" src="https://github.com/user-attachments/assets/dedb346e-5fc8-4778-bdf3-0858013ee395" />

<img width="1538" height="848" alt="image" src="https://github.com/user-attachments/assets/8ca3d3a6-796a-4709-b4b2-d62aea0f7daa" />

<img width="1576" height="898" alt="image" src="https://github.com/user-attachments/assets/494ff003-3439-4d16-90f4-39b4f87bb5ca" />

<img width="1512" height="856" alt="image" src="https://github.com/user-attachments/assets/1b92fd4f-82af-4af7-bcd0-c23d7636c056" />

3) Haemoglobin Level

<img width="1549" height="775" alt="image" src="https://github.com/user-attachments/assets/f11a7838-d326-4dca-9591-eb7c4d44c74c" />

