"""
src/llm/summarizer.py

Explainable medical report summarization using Phi-3 Mini (4-bit quantized).
Generates:
  1. Plain English clinical summary
  2. Per-flag reasoning trace (explainability layer)
  3. Recommended follow-up actions
  4. Patient-friendly summary

Runs fully offline via llama-cpp-python.
Model: Phi-3-mini-4k-instruct-q4.gguf (~2.2GB, fits 4GB VRAM)
"""

from pathlib import Path
from llama_cpp import Llama

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "phi-3-mini-4k-instruct-q4.gguf"

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Phi-3 Mini model not found at {MODEL_PATH}.\n"
                "Download it from: https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf\n"
                "Place the file at: models/phi-3-mini-4k-instruct-q4.gguf"
            )
        _llm = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=4096,
            n_gpu_layers=32,   # Offload to GPU — adjust if VRAM issues
            n_threads=4,
            verbose=False,
        )
    return _llm


def _run_inference(prompt: str, max_tokens: int = 512) -> str:
    """Run inference through Phi-3 Mini."""
    llm = _get_llm()
    output = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=0.2,      # Low temp for clinical accuracy
        top_p=0.9,
        repeat_penalty=1.1,
        stop=["<|end|>", "<|user|>"],
    )
    return output["choices"][0]["text"].strip()


def _build_clinical_context(entities: dict, flags: list[dict], trend_flags: list[dict]) -> str:
    """Build a structured context string from extracted entities and flags."""
    lines = []

    # Patient info
    patient = entities.get("patient", {})
    if any(patient.values()):
        lines.append("PATIENT:")
        if patient.get("name"):
            lines.append(f"  Name: {patient['name']}")
        if patient.get("age"):
            lines.append(f"  Age: {patient['age']}")
        if patient.get("gender"):
            lines.append(f"  Gender: {patient['gender']}")

    # Diagnoses
    diagnoses = entities.get("clinical", {}).get("diagnoses", [])
    if diagnoses:
        lines.append(f"\nDIAGNOSES: {', '.join(diagnoses)}")

    # Medications
    meds = entities.get("medications", [])
    if meds:
        med_strs = [
            f"{m['name']} {m['dosage'] or ''}".strip() for m in meds
        ]
        lines.append(f"\nMEDICATIONS: {', '.join(med_strs)}")

    # Abnormal flags
    abnormal = [f for f in flags if f["severity"] != "NORMAL"]
    if abnormal:
        lines.append("\nABNORMAL LAB VALUES:")
        for f in abnormal:
            lines.append(f"  [{f['severity']}] {f['message']}")

    # Trend flags
    if trend_flags:
        lines.append("\nLONGITUDINAL TRENDS:")
        for t in trend_flags:
            lines.append(f"  [{t['severity']}] {t['message']}")

    return "\n".join(lines)


def generate_clinical_summary(
    entities: dict,
    flags: list[dict],
    trend_flags: list[dict],
    raw_text_snippet: str = "",
) -> str:
    """
    Generate a plain English clinical summary for healthcare providers.
    """
    context = _build_clinical_context(entities, flags, trend_flags)

    prompt = f"""<|user|>
You are a clinical decision support assistant helping healthcare providers in India.
Based on the following extracted medical report data, write a clear, concise clinical summary in plain English.
Focus on the most important findings, abnormal values, and trends. Use medical terminology appropriately.
Keep the summary to 150-200 words.

EXTRACTED REPORT DATA:
{context}

Write the clinical summary below:
<|assistant|>
"""
    return _run_inference(prompt, max_tokens=300)


def generate_explainable_flags(flags: list[dict], trend_flags: list[dict]) -> list[dict]:
    """
    For each abnormal flag, generate an LLM reasoning trace explaining:
    - What the value means clinically
    - Which guideline was violated (ICMR source)
    - Why it matters
    - What follow-up is recommended

    This is the explainability layer (Gap 4).
    """
    abnormal = [f for f in flags if f["severity"] != "NORMAL"]
    explained = []

    for flag in abnormal:
        prompt = f"""<|user|>
You are a clinical assistant. Explain the following abnormal lab result in 2-3 sentences for a general practitioner.
Include: what this value indicates clinically, the Indian (ICMR) normal range, and what follow-up action is recommended.
Be specific and concise.

FLAG: {flag['message']}
GUIDELINE SOURCE: {flag.get('source', 'ICMR')}
NORMAL RANGE: {flag.get('normal_range', 'N/A')}

Explanation:
<|assistant|>
"""
        explanation = _run_inference(prompt, max_tokens=80)
        explained.append({
            **flag,
            "explanation": explanation,
        })

    # Add explanations for trend flags
    for trend in trend_flags:
        prompt = f"""<|user|>
You are a clinical assistant. Explain the following longitudinal trend in 2-3 sentences for a general practitioner.
Include: what this trend suggests clinically, the significance of the rate of change, and what follow-up is recommended.

TREND: {trend['message']}

Explanation:
<|assistant|>
"""
        explanation = _run_inference(prompt, max_tokens=80)
        explained.append({
            **trend,
            "type": "trend",
            "explanation": explanation,
        })

    return explained


def generate_patient_summary(
    entities: dict,
    flags: list[dict],
    trend_flags: list[dict],
) -> str:
    """
    Generate a plain language summary for patients (non-medical audience).
    Avoids jargon. Explains what the results mean in everyday language.
    """
    context = _build_clinical_context(entities, flags, trend_flags)
    abnormal_count = len([f for f in flags if f["severity"] != "NORMAL"])

    prompt = f"""<|user|>
You are a helpful medical assistant explaining lab results to a patient in India who has no medical background.
Write a friendly, clear explanation of their report in simple language (avoid medical jargon).
Mention how many values are outside normal range and whether they should see a doctor urgently.
Keep it to 100-150 words. Do not alarm unnecessarily, but be honest.

REPORT DATA:
{context}
ABNORMAL VALUES COUNT: {abnormal_count}

Patient-friendly explanation:
<|assistant|>
"""
    return _run_inference(prompt, max_tokens=200)


def generate_followup_actions(
    flags: list[dict],
    trend_flags: list[dict],
    diagnoses: list[str],
) -> list[str]:
    """
    Generate a prioritised list of recommended follow-up actions.
    """
    abnormal = [f for f in flags if f["severity"] in ("CRITICAL", "HIGH")]
    critical_tests = [f["test"] for f in abnormal if f["severity"] == "CRITICAL"]

    context_parts = []
    if critical_tests:
        context_parts.append(f"CRITICAL values: {', '.join(critical_tests)}")
    if trend_flags:
        trend_tests = [t["test"] for t in trend_flags]
        context_parts.append(f"Worsening trends: {', '.join(trend_tests)}")
    if diagnoses:
        context_parts.append(f"Known diagnoses: {', '.join(diagnoses)}")

    if not context_parts:
        return ["No urgent follow-up actions required. Routine monitoring recommended."]

    context = "\n".join(context_parts)

    prompt = f"""<|user|>
Based on the following clinical findings, provide a numbered list of 3-5 specific follow-up actions
for a general practitioner in India. Be specific and actionable. Prioritise by urgency.

FINDINGS:
{context}

Follow-up actions:
<|assistant|>
"""
    response = _run_inference(prompt, max_tokens=200)

    # Parse numbered list from response
    lines = [
        line.strip()
        for line in response.split("\n")
        if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith("-"))
    ]
    return lines if lines else [response]


def run_full_analysis(
    entities: dict,
    flags: list[dict],
    trend_flags: list[dict],
    raw_text_snippet: str = "",
    verify: bool = True,
) -> dict:
    """
    Run complete LLM analysis pipeline.

    If verify=True, the clinical and patient summaries are passed through
    the verification agent (src/llm/verification_agent.py) before being
    returned. This is the multi-agent handoff: a generation agent produces
    the summary, a verification agent audits it against ground-truth
    extracted data, and corrects it if it finds unsupported claims.

    Returns all generated outputs in one dict, plus a "verification" key
    describing what the verification agent found (only present if verify=True).
    """
    diagnoses = entities.get("clinical", {}).get("diagnoses", [])

    clinical_summary_raw = generate_clinical_summary(
        entities, flags, trend_flags, raw_text_snippet
    )
    patient_summary_raw = generate_patient_summary(
        entities, flags, trend_flags
    )

    result = {
        "clinical_summary": clinical_summary_raw,
        "patient_summary": patient_summary_raw,
        "explained_flags": generate_explainable_flags(flags, trend_flags),
        "followup_actions": generate_followup_actions(
            flags, trend_flags, diagnoses
        ),
    }

    if not verify:
        return result

    # Lazy import avoids a circular import at module load time
    from src.llm.verification_agent import verify_and_correct

    clinical_check = verify_and_correct(
        clinical_summary_raw, entities, flags, trend_flags, "clinical"
    )
    patient_check = verify_and_correct(
        patient_summary_raw, entities, flags, trend_flags, "patient"
    )

    result["clinical_summary"] = clinical_check["final_summary"]
    result["patient_summary"]  = patient_check["final_summary"]
    result["verification"] = {
        "clinical_summary_corrected": clinical_check["was_corrected"],
        "patient_summary_corrected": patient_check["was_corrected"],
        "clinical_verifier_notes": clinical_check["verification"]["verifier_notes"],
        "patient_verifier_notes": patient_check["verification"]["verifier_notes"],
    }

    return result
