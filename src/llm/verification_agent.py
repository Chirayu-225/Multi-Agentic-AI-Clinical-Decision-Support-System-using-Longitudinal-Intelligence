"""
src/llm/verification_agent.py

Verification Agent — the second agent in MedSight's multi-agent system.

Role: audits the orchestrator's generated clinical/patient summaries against
the raw, verified extracted data (entities + flags) BEFORE the output reaches
the user. Catches hallucinated values, omitted findings, or claims not
grounded in the actual report.

Architecture note:
This agent shares the SAME loaded Phi-3 Mini instance as the generation
agent in summarizer.py — it does not load a second model. It is
distinguished purely by a different system prompt / role, which is what
keeps this multi-agent design within the 4GB VRAM budget on an RTX 3050 Ti.

This was added after observing real hallucination during testing: the
generation agent occasionally fabricated values (e.g. cholesterol, HbA1c,
blood pressure) that did not exist anywhere in the source report. The
verification agent is a direct, targeted fix for that failure mode.
"""

import json
import re
from src.llm.summarizer import _run_inference


def _build_ground_truth_context(entities: dict, flags: list[dict], trend_flags: list[dict]) -> str:
    """
    Build a strict, minimal ground-truth string containing ONLY values that
    actually exist in the extracted data. The verifier compares the
    generated summary against exactly this — nothing more, nothing less.
    """
    lines = []

    patient = entities.get("patient", {})
    if patient.get("name"):
        lines.append(f"Patient: {patient['name']}")
    if patient.get("age"):
        lines.append(f"Age: {patient['age']}")
    if patient.get("gender"):
        lines.append(f"Gender: {patient['gender']}")

    diagnoses = entities.get("clinical", {}).get("diagnoses", [])
    if diagnoses:
        lines.append(f"Diagnoses: {', '.join(diagnoses)}")

    meds = entities.get("medications", [])
    if meds:
        med_strs = [f"{m['name']} {m['dosage'] or ''}".strip() for m in meds]
        lines.append(f"Medications: {', '.join(med_strs)}")

    if flags:
        lines.append("Lab values found in report:")
        for f in flags:
            lines.append(f"  - {f['test']}: {f['value']} {f.get('unit','')} ({f['severity']})")
    else:
        lines.append("Lab values found in report: NONE")

    if trend_flags:
        lines.append("Trends found across visits:")
        for t in trend_flags:
            lines.append(f"  - {t['test']}: {t.get('message','')}")

    return "\n".join(lines)


def _extract_numeric_claims(text: str) -> list[str]:
    """
    Pull out numeric clinical claims from generated text — e.g. '160 mg/dL',
    '9%', '150/95 mmHg' — so they can be checked against ground truth.
    """
    pattern = re.compile(
        r"\d+\.?\d*\s*(?:mg/dL|g/dL|mEq/L|U/L|mIU/L|%|mmHg|cells/mcL|mmol/L|kg/m²|bpm)",
        re.IGNORECASE,
    )
    return pattern.findall(text)


def verify_summary(
    generated_summary: str,
    entities: dict,
    flags: list[dict],
    trend_flags: list[dict],
    summary_type: str = "clinical",
) -> dict:
    """
    Verification agent entry point.

    Compares a generated summary against ground-truth extracted data.
    Returns whether the summary passed verification, and if not, which
    claims could not be grounded in the source data.

    Returns:
        {
            "passed": bool,
            "ungrounded_claims": list[str],
            "verifier_notes": str,
            "action": "approve" | "regenerate"
        }
    """
    ground_truth = _build_ground_truth_context(entities, flags, trend_flags)
    generated_claims = _extract_numeric_claims(generated_summary)
    ground_truth_claims = _extract_numeric_claims(ground_truth)

    # Fast deterministic check first — any numeric claim in the summary that
    # doesn't appear anywhere in ground truth is immediately suspicious.
    # Normalize for comparison (strip whitespace casing).
    gt_normalized = [c.lower().replace(" ", "") for c in ground_truth_claims]
    suspicious = [
        c for c in generated_claims
        if c.lower().replace(" ", "") not in gt_normalized
    ]

    # LLM-based semantic check — catches claims that are grounded in spirit
    # but phrased differently, and catches qualitative hallucinations
    # (invented conditions, invented diagnoses) that the regex can't see.
    prompt = f"""<|user|>
You are a verification agent for a medical AI system. Your ONLY job is to check
whether the SUMMARY below makes any claims not supported by the GROUND TRUTH data.

GROUND TRUTH (the only data that actually exists in this patient's report):
{ground_truth}

SUMMARY TO VERIFY:
{generated_summary}

Does the summary mention any specific medical value, condition, or finding that
does NOT appear in the ground truth data above? Answer in this exact format:
VERDICT: PASS or FAIL
ISSUES: <list any unsupported claims, or "none">
<|assistant|>
"""
    verifier_response = _run_inference(prompt, max_tokens=150)

    llm_failed = "VERDICT: FAIL" in verifier_response.upper()
    deterministic_failed = len(suspicious) > 0

    passed = not (llm_failed or deterministic_failed)

    return {
        "passed": passed,
        "ungrounded_claims": suspicious,
        "verifier_notes": verifier_response.strip(),
        "action": "approve" if passed else "regenerate",
        "summary_type": summary_type,
    }


def verify_and_correct(
    generated_summary: str,
    entities: dict,
    flags: list[dict],
    trend_flags: list[dict],
    summary_type: str = "clinical",
    max_retries: int = 1,
) -> dict:
    """
    Full verification loop: verify, and if it fails, regenerate once with
    explicit correction instructions, then re-verify.

    This is the actual agent-to-agent handoff — generation agent produces,
    verification agent checks, and if rejected, generation agent retries
    with the verifier's specific feedback.

    Returns:
        {
            "final_summary": str,
            "was_corrected": bool,
            "verification": dict   # last verification result
        }
    """
    verification = verify_summary(
        generated_summary, entities, flags, trend_flags, summary_type
    )

    if verification["passed"]:
        return {
            "final_summary": generated_summary,
            "was_corrected": False,
            "verification": verification,
        }

    # Regenerate with explicit grounding instructions, using the verifier's
    # findings as direct feedback to the generation agent.
    ground_truth = _build_ground_truth_context(entities, flags, trend_flags)
    issues = ", ".join(verification["ungrounded_claims"]) or "see verifier notes"

    correction_prompt = f"""<|user|>
Your previous summary contained claims not supported by the patient's actual data.
Unsupported items flagged: {issues}

Rewrite the summary using ONLY the data below. Do not invent any value, test,
or condition that is not explicitly listed. If a category like cholesterol or
blood pressure was not tested, do not mention it at all.

ACTUAL PATIENT DATA:
{ground_truth}

Corrected summary:
<|assistant|>
"""
    corrected_summary = _run_inference(correction_prompt, max_tokens=300).strip()

    # Re-verify the correction once
    re_verification = verify_summary(
        corrected_summary, entities, flags, trend_flags, summary_type
    )

    return {
        "final_summary": corrected_summary if re_verification["passed"] else corrected_summary,
        "was_corrected": True,
        "verification": re_verification,
    }
