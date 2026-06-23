"""
app/streamlit_app.py
MedSight — Offline Clinical Intelligence Platform
Enhanced UI with clinical-grade aesthetics.
"""

import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="MedSight · Clinical Intelligence",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"] {
  background: #080C14 !important;
  font-family: 'Inter', sans-serif;
}
[data-testid="stAppViewContainer"] > .main { background: #080C14; }
[data-testid="block-container"] { padding: 2rem 2.5rem; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: #0B0F1A !important;
  border-right: 1px solid #1A2035;
}
[data-testid="stSidebar"] > div { padding: 1.5rem 1.2rem; }

/* ── Logo ── */
.ms-logo {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 6px;
}
.ms-logo-mark {
  width: 36px; height: 36px; border-radius: 9px;
  background: linear-gradient(135deg, #1E6FD9 0%, #0EA5E9 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
  box-shadow: 0 0 16px #1E6FD940;
}
.ms-logo-text { font-size: 20px; font-weight: 700; color: #E8F0FE; letter-spacing: -0.3px; }
.ms-logo-sub { font-size: 12px; color: #3D5070; margin-bottom: 1.5rem; padding-left: 46px; letter-spacing: 0.04em; }

/* ── Nav ── */
.stRadio > div { gap: 2px !important; }
.stRadio label {
  display: block !important; padding: 10px 12px !important;
  border-radius: 7px !important; font-size: 15px !important;
  color: #4B6080 !important; cursor: pointer !important;
  transition: all 0.15s !important;
}
.stRadio label:hover { background: #111827 !important; color: #94AFCF !important; }
[data-baseweb="radio"] input:checked + div + label,
.stRadio [aria-checked="true"] label { background: #111C2D !important; color: #60A5FA !important; }

/* ── Security badge ── */
.sec-badge {
  margin-top: auto; padding: 12px 14px;
  background: #0D1520; border: 1px solid #1A2A3A;
  border-radius: 8px; font-size: 13px; color: #2D4A6A;
  line-height: 1.7;
}
.sec-badge span { color: #1E6FD9; font-weight: 600; }

/* ── Page header ── */
.page-eyebrow { font-size: 13px; color: #1E6FD9; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 6px; }
.page-title { font-size: 30px; font-weight: 700; color: #E8F0FE; letter-spacing: -0.5px; margin-bottom: 6px; }
.page-sub { font-size: 15px; color: #3D5070; margin-bottom: 2rem; }

/* ── Upload zone ── */
.upload-zone {
  border: 1.5px dashed #1A2A3A; border-radius: 12px;
  background: #0B0F1A; padding: 2rem;
  transition: border-color 0.2s;
}
[data-testid="stFileUploader"] {
  background: #0B0F1A !important;
  border: 1.5px dashed #1A2A3A !important;
  border-radius: 12px !important;
}

/* ── Input fields ── */
.stTextInput input, .stDateInput input {
  background: #0B0F1A !important;
  border: 1px solid #1A2A3A !important;
  border-radius: 8px !important;
  color: #94AFCF !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 13px !important;
}
.stTextInput input:focus, .stDateInput input:focus {
  border-color: #1E6FD9 !important;
  box-shadow: 0 0 0 3px #1E6FD920 !important;
}
.stTextInput label, .stDateInput label, .stFileUploader label {
  color: #3D5070 !important; font-size: 11px !important;
  font-weight: 600 !important; letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
}

/* ── Primary button ── */
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #1E6FD9, #0EA5E9) !important;
  border: none !important; border-radius: 8px !important;
  font-weight: 600 !important; font-size: 13px !important;
  color: white !important; letter-spacing: 0.02em !important;
  padding: 0.6rem 1.4rem !important;
  box-shadow: 0 4px 16px #1E6FD930 !important;
  transition: all 0.2s !important;
}
.stButton > button[kind="primary"]:hover {
  box-shadow: 0 6px 24px #1E6FD950 !important;
  transform: translateY(-1px) !important;
}

/* ── Risk banner ── */
.risk-banner {
  border-radius: 12px; padding: 18px 22px; margin-bottom: 20px;
  display: flex; align-items: center; justify-content: space-between;
  border: 1px solid;
}
.risk-banner-left { display: flex; align-items: center; gap: 14px; }
.risk-pulse {
  width: 10px; height: 10px; border-radius: 50%;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}
.risk-banner-title { font-size: 15px; font-weight: 700; }
.risk-banner-sub { font-size: 12px; color: #4B6080; margin-top: 2px; }
.risk-pills { display: flex; gap: 6px; flex-wrap: wrap; }
.rpill {
  padding: 3px 10px; border-radius: 20px; font-size: 11px;
  font-weight: 600; font-family: 'JetBrains Mono', monospace;
}

/* ── Section header ── */
.sec-head {
  font-size: 12px; font-weight: 600; color: #3D5070;
  text-transform: uppercase; letter-spacing: 0.1em;
  padding-bottom: 8px; border-bottom: 1px solid #1A2035;
  margin-bottom: 12px; margin-top: 20px;
}

/* ── Risk cards ── */
.rcard {
  border-radius: 10px; padding: 16px 18px; margin-bottom: 8px;
  border: 1px solid; border-left-width: 3px;
  transition: transform 0.15s;
}
.rcard:hover { transform: translateX(2px); }
.rcard-critical { background: #160A0A; border-color: #EF4444; border-left-color: #EF4444; }
.rcard-high     { background: #130D05; border-color: #F97316; border-left-color: #F97316; }
.rcard-moderate { background: #131008; border-color: #EAB308; border-left-color: #EAB308; }
.rcard-normal   { background: #08130D; border-color: #22C55E; border-left-color: #22C55E; }
.rcard-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}
.rcard-label { font-size: 14px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; }
.rcard-badge {
  font-size: 13px; font-weight: 600; padding: 3px 9px;
  border-radius: 4px; font-family: 'JetBrains Mono', monospace;
}
.rcard-msg { font-size: 16px; color: #8FA8C2; line-height: 1.8; }
.rcard-exp {
  margin-top: 12px; padding-top: 12px; border-top: 1px solid #1A2035;
  font-size: 15px; color: #5A7090; line-height: 1.8; font-style: italic;
}
.rcard-exp::before { content: "↳ "; color: #1E6FD9; font-style: normal; }

/* ── Summary cards ── */
.scard {
  background: #0B0F1A; border: 1px solid #1A2035;
  border-radius: 12px; padding: 18px 20px; margin-bottom: 12px;
}
.scard-label {
  font-size: 13px; font-weight: 600; color: #1E6FD9;
  letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 10px;
  display: flex; align-items: center; gap: 6px;
}
.scard-label::before {
  content: ""; display: inline-block; width: 3px; height: 12px;
  background: #1E6FD9; border-radius: 2px;
}
.scard-body { font-size: 16px; color: #8FA8C2; line-height: 1.9; }

/* ── Action items ── */
.aitem {
  background: #0B0F1A; border: 1px solid #1A2035;
  border-radius: 8px; padding: 14px 18px; margin-bottom: 8px;
  font-size: 16px; color: #8FA8C2; line-height: 1.7;
  display: flex; align-items: flex-start; gap: 12px;
}
.aitem-num {
  font-family: 'JetBrains Mono', monospace; font-size: 14px;
  color: #1E6FD9; font-weight: 600; flex-shrink: 0; padding-top: 1px;
}

/* ── Entity tags ── */
.etag {
  display: inline-block; background: #0D1825; border: 1px solid #1A3050;
  border-radius: 5px; padding: 5px 12px; font-size: 14px; color: #60A5FA;
  margin: 3px; font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.02em;
}
.etag-med { border-color: #1A3530; color: #34D399; background: #0D1A17; }

/* ── Patient metric cards ── */
.pmcard {
  background: #0B0F1A; border: 1px solid #1A2035;
  border-radius: 10px; padding: 14px 16px; text-align: center;
}
.pmcard-label { font-size: 12px; color: #3D5070; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px; }
.pmcard-value { font-size: 19px; font-weight: 600; color: #94AFCF; font-family: 'JetBrains Mono', monospace; }

/* ── Doc info strip ── */
.doc-strip {
  display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap;
}
.dchip {
  background: #0B0F1A; border: 1px solid #1A2035; border-radius: 6px;
  padding: 9px 16px; font-size: 14px; color: #5A7090;
  font-family: 'JetBrains Mono', monospace;
}
.dchip span { color: #60A5FA; font-weight: 500; }

/* ── Divider ── */
hr { border: none; border-top: 1px solid #1A2035 !important; margin: 1.5rem 0 !important; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
.stSpinner > div { border-top-color: #1E6FD9 !important; }

/* ── Selectbox ── */
.stSelectbox > div > div {
  background: #0B0F1A !important; border-color: #1A2A3A !important;
  color: #94AFCF !important; border-radius: 8px !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
  background: #0B0F1A !important; border: 1px solid #1A2035 !important;
  border-radius: 8px !important; color: #4B6080 !important; font-size: 13px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="ms-logo">
      <div class="ms-logo-mark">🩺</div>
      <div class="ms-logo-text">MedSight</div>
    </div>
    <div class="ms-logo-sub">CLINICAL INTELLIGENCE · OFFLINE</div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "nav",
        ["Analyse Report", "Patient History", "About"],
        label_visibility="collapsed",
    )

    st.markdown("<br>" * 6, unsafe_allow_html=True)
    st.markdown("""
    <div class="sec-badge">
      <span>🔒 Fully offline.</span><br>
      No patient data leaves this device.<br>
      All inference runs locally on your GPU.
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
COLOR = {
    "CRITICAL": "#EF4444",
    "HIGH":     "#F97316",
    "MODERATE": "#EAB308",
    "NORMAL":   "#22C55E",
}

def sev_css(sev):
    return {"CRITICAL": "rcard-critical", "HIGH": "rcard-high",
            "MODERATE": "rcard-moderate", "NORMAL": "rcard-normal"}.get(sev, "rcard-normal")

def rpill_style(sev):
    bg = {"CRITICAL": "#EF444420", "HIGH": "#F9731620",
          "MODERATE": "#EAB30820", "NORMAL": "#22C55E20"}.get(sev, "#22C55E20")
    return f'background:{bg};color:{COLOR.get(sev,"#22C55E")};'


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Analyse Report
# ══════════════════════════════════════════════════════════════════════════════
if page == "Analyse Report":
    st.markdown("""
    <div class="page-eyebrow">Clinical Analysis</div>
    <div class="page-title">Analyse Medical Report</div>
    <div class="page-sub">Upload a patient report to extract findings, flag risks against ICMR reference ranges, and generate an explainable clinical summary.</div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2.2, 1, 1])
    with c1:
        uploaded_file = st.file_uploader(
            "REPORT PDF",
            type=["pdf"],
            help="Supports digital and scanned PDFs, including Hindi/English mixed reports.",
        )
    with c2:
        patient_id = st.text_input(
            "PATIENT ID",
            placeholder="PT-2024-001",
            help="Used for longitudinal tracking across visits.",
        )
    with c3:
        report_date = st.date_input("REPORT DATE", value=datetime.today())

    st.markdown("<br>", unsafe_allow_html=True)

    if uploaded_file and patient_id:
        if st.button("Run Analysis", use_container_width=True, type="primary"):
            with st.spinner("Extracting entities · Flagging risks · Generating summary…"):
                try:
                    response = requests.post(
                        f"{API_URL}/report/upload",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                        data={"patient_id": patient_id, "report_date": str(report_date)},
                        timeout=600,
                    )
                    if response.status_code == 200:
                        st.session_state["last_result"] = response.json()
                    else:
                        st.error(f"API error {response.status_code}: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach MedSight API — make sure the backend is running on port 8000.")
                except requests.exceptions.ReadTimeout:
                    st.error("Request timed out — the model may still be loading. Wait 30 seconds and try again.")

    # ── Landing state — shown when no result yet ──────────────────────────────
    if "last_result" not in st.session_state:
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Pipeline visual ────────────────────────────────────────────────
        st.markdown('<div style="font-size:13px;font-weight:600;color:#1E6FD9;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:12px;">How It Works</div>', unsafe_allow_html=True)

        steps = [
            ("📄", "Ingest", "PyMuPDF · EasyOCR · Hindi transliteration"),
            ("🔬", "Extract", "GLiNER NER · Entities · Lab values"),
            ("⚠️", "Flag", "ICMR reference ranges · Trend analysis"),
            ("🧠", "Summarise", "Phi-3 Mini 4-bit · Explainable output"),
            ("📊", "Track", "ChromaDB history · Longitudinal trends"),
        ]
        pipe_cols = st.columns(len(steps))
        for col, (icon, title, desc) in zip(pipe_cols, steps):
            col.markdown(f"""
            <div style="text-align:center;background:#0B0F1A;border:1px solid #1A2035;border-radius:10px;padding:20px 8px;">
              <div style="font-size:28px;margin-bottom:10px;">{icon}</div>
              <div style="font-size:16px;font-weight:600;color:#94AFCF;margin-bottom:8px;">{title}</div>
              <div style="font-size:13px;color:#5A7090;line-height:1.8;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Feature cards + severity legend side by side ───────────────────
        fc1, fc2 = st.columns([1.3, 1], gap="large")

        with fc1:
            st.markdown("""
            <div style="font-size:13px;font-weight:600;color:#3D5070;letter-spacing:0.1em;text-transform:uppercase;padding-bottom:8px;border-bottom:1px solid #1A2035;margin-bottom:12px;">Key Capabilities</div>
            """, unsafe_allow_html=True)

            caps = [
                ("🇮🇳", "#1E6FD9", "ICMR-Grounded Risk Flagging", "Checks lab values against Indian Council of Medical Research reference ranges — not Western defaults. Gender-specific thresholds included."),
                ("📈", "#22C55E", "Longitudinal Trend Detection", "Flags consistently worsening values across multiple visits even when no single reading crosses a critical threshold."),
                ("💡", "#EAB308", "Explainable Reasoning", "Every flag shows the violated guideline, clinical significance, and a specific recommended follow-up action."),
                ("🌐", "#A78BFA", "Hindi/English Mixed Reports", "EasyOCR + indic-transliteration handles scanned Indian lab reports with Devanagari annotations."),
            ]
            for icon, col, title, desc in caps:
                st.markdown(f"""
                <div style="display:flex;gap:12px;align-items:flex-start;padding:12px 14px;background:#0B0F1A;border:1px solid #1A2035;border-radius:10px;margin-bottom:8px;">
                  <div style="font-size:18px;flex-shrink:0;margin-top:1px;">{icon}</div>
                  <div>
                    <div style="font-size:16px;font-weight:600;color:{col};margin-bottom:5px;">{title}</div>
                    <div style="font-size:14px;color:#5A7090;line-height:1.8;">{desc}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        with fc2:
            st.markdown("""
            <div style="font-size:13px;font-weight:600;color:#3D5070;letter-spacing:0.1em;text-transform:uppercase;padding-bottom:8px;border-bottom:1px solid #1A2035;margin-bottom:12px;">Risk Severity Levels</div>
            """, unsafe_allow_html=True)

            levels = [
                ("#EF4444", "CRITICAL", "Value at or beyond critical threshold. Requires immediate clinical attention. E.g. Hemoglobin ≤ 7.0 g/dL."),
                ("#F97316", "HIGH", "More than 20% outside normal range. Clinically significant — follow-up recommended within days."),
                ("#EAB308", "MODERATE", "Borderline deviation from ICMR range. Monitor closely and retest at next visit."),
                ("#22C55E", "NORMAL", "Value within ICMR reference range for patient's age and gender profile."),
            ]
            for col, label, desc in levels:
                st.markdown(f"""
                <div style="border-left:3px solid {col};background:{col}0D;border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:10px;">
                  <div style="font-size:14px;font-weight:700;color:{col};letter-spacing:0.1em;margin-bottom:6px;">{label}</div>
                  <div style="font-size:14px;color:#5A7090;line-height:1.8;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

            # Supported formats
            st.markdown("""
            <div style="font-size:13px;font-weight:600;color:#3D5070;letter-spacing:0.1em;text-transform:uppercase;padding-bottom:8px;border-bottom:1px solid #1A2035;margin:16px 0 12px;">Supported Report Types</div>
            """, unsafe_allow_html=True)
            formats = ["Discharge Summary", "Lab Report", "Radiology Note", "Pathology Report", "Prescription", "OPD Summary"]
            st.markdown(" ".join([f'<span class="etag">{f}</span>' for f in formats]), unsafe_allow_html=True)

    # ── Results ───────────────────────────────────────────────────────────────
    if "last_result" in st.session_state:
        result    = st.session_state["last_result"]
        risk      = result.get("risk_summary", {})
        entities  = result.get("entities", {})
        rule_flags = result.get("rule_flags", [])
        trend_flags = result.get("trend_flags", [])
        llm       = result.get("llm_output", {})
        severity  = risk.get("overall_severity", "NORMAL")
        bc        = COLOR.get(severity, "#22C55E")

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Risk banner ────────────────────────────────────────────────────
        banner_title = "⚠ CRITICAL — Immediate Attention Required" if severity == "CRITICAL" else f"Risk Level · {severity}"
        st.markdown(f"""
        <div class="risk-banner" style="background:{bc}0D;border-color:{bc}40;">
          <div class="risk-banner-left">
            <div class="risk-pulse" style="background:{bc};box-shadow:0 0 8px {bc};"></div>
            <div>
              <div class="risk-banner-title" style="color:{bc};">{banner_title}</div>
              <div class="risk-banner-sub">Report · {result.get('filename','—')} · {result.get('pages','?')} page(s) · {result.get('source_type','').title()}</div>
            </div>
          </div>
          <div class="risk-pills">
            <span class="rpill" style="{rpill_style('CRITICAL')}">{risk.get('critical_count',0)} Critical</span>
            <span class="rpill" style="{rpill_style('HIGH')}">{risk.get('high_count',0)} High</span>
            <span class="rpill" style="{rpill_style('MODERATE')}">{risk.get('trend_count',0)} Trends</span>
            <span class="rpill" style="background:#1A2035;color:#4B6080;">{risk.get('total_flags',0)} Total</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Two-column layout ──────────────────────────────────────────────
        left, right = st.columns([1.1, 1], gap="large")

        with left:
            # Risk flags
            st.markdown('<div class="sec-head">Risk Flags</div>', unsafe_allow_html=True)
            explained     = llm.get("explained_flags", [])
            explained_map = {f.get("test", f.get("canonical", "")): f for f in explained}
            abnormal      = [f for f in rule_flags if f["severity"] != "NORMAL"]

            if not abnormal and not trend_flags:
                st.markdown("""
                <div class="rcard rcard-normal">
                  <div class="rcard-head">
                    <div class="rcard-label" style="color:#22C55E;">All Clear</div>
                    <div class="rcard-badge" style="background:#22C55E20;color:#22C55E;">NORMAL</div>
                  </div>
                  <div class="rcard-msg">All extracted lab values are within ICMR reference ranges.</div>
                </div>
                """, unsafe_allow_html=True)

            for flag in abnormal:
                sev  = flag["severity"]
                col  = COLOR.get(sev, "#9CA3AF")
                exp  = explained_map.get(flag.get("test", ""), {}).get("explanation", "")
                val_str = f"{flag.get('value','')} {flag.get('unit','')}".strip()
                st.markdown(f"""
                <div class="rcard {sev_css(sev)}">
                  <div class="rcard-head">
                    <div class="rcard-label" style="color:{col};">{flag.get('test','')}</div>
                    <div class="rcard-badge" style="background:{col}20;color:{col};">{sev} · {val_str}</div>
                  </div>
                  <div class="rcard-msg">{flag.get('message','')}</div>
                  {'<div class="rcard-exp">' + exp + '</div>' if exp else ''}
                </div>
                """, unsafe_allow_html=True)

            for trend in trend_flags:
                sev = trend.get("severity", "MODERATE")
                col = COLOR.get(sev, "#EAB308")
                exp = trend.get("explanation", "")
                vals = " → ".join(str(v) for v in trend.get("values_over_time", []))
                st.markdown(f"""
                <div class="rcard {sev_css(sev)}">
                  <div class="rcard-head">
                    <div class="rcard-label" style="color:{col};">📈 Trend · {trend.get('test','').replace('_',' ').title()}</div>
                    <div class="rcard-badge" style="background:{col}20;color:{col};">{trend.get('total_change_pct','')}% change</div>
                  </div>
                  <div class="rcard-msg" style="font-family:'JetBrains Mono',monospace;font-size:11px;margin-bottom:6px;">{vals} {trend.get('unit','')}</div>
                  <div class="rcard-msg">{trend.get('message','')}</div>
                  {'<div class="rcard-exp">' + exp + '</div>' if exp else ''}
                </div>
                """, unsafe_allow_html=True)

            # Follow-up actions
            st.markdown('<div class="sec-head">Recommended Actions</div>', unsafe_allow_html=True)
            actions = llm.get("followup_actions", [])
            if actions:
                for i, action in enumerate(actions, 1):
                    st.markdown(f"""
                    <div class="aitem">
                      <div class="aitem-num">{i:02d}</div>
                      <div>{action}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="aitem"><div class="aitem-num">—</div><div>No urgent actions required. Routine monitoring advised.</div></div>', unsafe_allow_html=True)

        with right:
            verification = llm.get("verification", {})

            # Clinical summary
            st.markdown('<div class="sec-head">Clinical Summary</div>', unsafe_allow_html=True)
            clinical_corrected = verification.get("clinical_summary_corrected", False)
            verify_badge = (
                '<span style="font-size:11px;font-weight:600;color:#EAB308;background:#EAB30820;padding:2px 8px;border-radius:4px;margin-left:8px;">✓ verified-agent corrected</span>'
                if clinical_corrected else
                '<span style="font-size:11px;font-weight:600;color:#22C55E;background:#22C55E20;padding:2px 8px;border-radius:4px;margin-left:8px;">✓ verified</span>'
            )
            st.markdown(f"""
            <div class="scard">
              <div class="scard-label">For Healthcare Provider{verify_badge}</div>
              <div class="scard-body">{llm.get("clinical_summary", "Processing…")}</div>
            </div>
            """, unsafe_allow_html=True)

            # Patient summary
            st.markdown('<div class="sec-head">Patient Summary</div>', unsafe_allow_html=True)
            patient_corrected = verification.get("patient_summary_corrected", False)
            verify_badge_p = (
                '<span style="font-size:11px;font-weight:600;color:#EAB308;background:#EAB30820;padding:2px 8px;border-radius:4px;margin-left:8px;">✓ verified-agent corrected</span>'
                if patient_corrected else
                '<span style="font-size:11px;font-weight:600;color:#22C55E;background:#22C55E20;padding:2px 8px;border-radius:4px;margin-left:8px;">✓ verified</span>'
            )
            st.markdown(f"""
            <div class="scard">
              <div class="scard-label">In Plain Language{verify_badge_p}</div>
              <div class="scard-body">{llm.get("patient_summary", "Processing…")}</div>
            </div>
            """, unsafe_allow_html=True)

            # Extracted entities
            patient = entities.get("patient", {})
            if any(patient.values()):
                st.markdown('<div class="sec-head">Patient Info</div>', unsafe_allow_html=True)
                pc = st.columns(3)
                items = [("Name", patient.get("name")), ("Age", patient.get("age")), ("Gender", patient.get("gender"))]
                for col, (label, val) in zip(pc, items):
                    if val:
                        col.markdown(f'<div class="pmcard"><div class="pmcard-label">{label}</div><div class="pmcard-value">{val}</div></div>', unsafe_allow_html=True)

            diagnoses = entities.get("clinical", {}).get("diagnoses", [])
            if diagnoses:
                st.markdown('<div class="sec-head">Diagnoses</div>', unsafe_allow_html=True)
                st.markdown(" ".join([f'<span class="etag">{d}</span>' for d in diagnoses]), unsafe_allow_html=True)

            meds = entities.get("medications", [])
            if meds:
                st.markdown('<div class="sec-head">Medications</div>', unsafe_allow_html=True)
                st.markdown(" ".join([f'<span class="etag etag-med">{m["name"]}</span>' for m in meds]), unsafe_allow_html=True)

        # ── Doc info strip ─────────────────────────────────────────────────
        st.markdown(f"""
        <div class="doc-strip">
          <div class="dchip">Source <span>{result.get('source_type','').title()}</span></div>
          <div class="dchip">Pages <span>{result.get('pages','?')}</span></div>
          <div class="dchip">Hindi <span>{'Yes' if result.get('has_hindi') else 'No'}</span></div>
          <div class="dchip">Report ID <span>{result.get('report_id','')[:8]}…</span></div>
          <div class="dchip">Patient <span>{result.get('patient_id','')}</span></div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Patient History
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Patient History":
    st.markdown("""
    <div class="page-eyebrow">Longitudinal Tracking</div>
    <div class="page-title">Patient History</div>
    <div class="page-sub">View lab value trends and risk patterns across multiple visits for any patient.</div>
    """, unsafe_allow_html=True)

    patient_id = st.text_input("PATIENT ID", placeholder="PT-2024-001")

    if patient_id:
        try:
            response = requests.get(f"{API_URL}/patient/{patient_id}/history", timeout=10)
            if response.status_code == 200:
                data    = response.json()
                reports = data.get("reports", [])

                if not reports:
                    st.markdown(f"""
                    <div class="scard" style="text-align:center;padding:2.5rem;">
                      <div style="font-size:28px;margin-bottom:10px;">📭</div>
                      <div style="color:#3D5070;font-size:13px;">No reports found for <span style="color:#60A5FA;font-family:'JetBrains Mono',monospace;">{patient_id}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="font-size:12px;color:#3D5070;margin-bottom:1rem;">
                      <span style="color:#60A5FA;font-family:'JetBrains Mono',monospace;">{patient_id}</span>
                      · {len(reports)} report(s) on record
                    </div>
                    """, unsafe_allow_html=True)

                    # Collect lab tests
                    all_tests = set()
                    for r in reports:
                        for lab in r.get("lab_values", []):
                            if lab.get("value") is not None:
                                all_tests.add(lab["test"])

                    if all_tests:
                        st.markdown('<div class="sec-head">Lab Value Trend</div>', unsafe_allow_html=True)
                        selected_test = st.selectbox("SELECT LAB TEST", sorted(all_tests), label_visibility="collapsed")

                        dates, values = [], []
                        for r in reports:
                            for lab in r.get("lab_values", []):
                                if lab["test"] == selected_test and lab.get("value") is not None:
                                    dates.append(r["report_date"])
                                    values.append(float(lab["value"]))

                        if len(values) >= 2:
                            # Colour line by trend direction
                            if values[-1] < values[0]:
                                trend_color = "#EF4444"
                                fill_color  = "rgba(239,68,68,0.06)"
                            elif values[-1] > values[0]:
                                trend_color = "#22C55E"
                                fill_color  = "rgba(34,197,94,0.06)"
                            else:
                                trend_color = "#60A5FA"
                                fill_color  = "rgba(96,165,250,0.06)"

                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=dates, y=values,
                                mode="lines+markers",
                                name=selected_test,
                                line=dict(color=trend_color, width=2.5),
                                marker=dict(size=8, color=trend_color,
                                            line=dict(color="#080C14", width=2)),
                                fill="tozeroy",
                                fillcolor=fill_color,
                            ))
                            fig.update_layout(
                                paper_bgcolor="#0B0F1A",
                                plot_bgcolor="#080C14",
                                font=dict(color="#4B6080", family="Inter"),
                                xaxis=dict(gridcolor="#1A2035", title="Visit Date",
                                           tickfont=dict(size=11, family="JetBrains Mono")),
                                yaxis=dict(gridcolor="#1A2035", title="Value",
                                           tickfont=dict(size=11, family="JetBrains Mono")),
                                margin=dict(l=10, r=10, t=20, b=10),
                                height=280,
                                showlegend=False,
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        elif len(values) == 1:
                            st.info("Only one data point — upload more reports for this patient to see trends.")

                    # Report cards
                    st.markdown('<div class="sec-head">Visit History</div>', unsafe_allow_html=True)
                    for r in reversed(reports):
                        with st.expander(f"📄  {r['filename']}  ·  {r['report_date']}"):
                            if r.get("diagnoses"):
                                st.markdown(f"**Diagnoses** · " + " ".join([f'<span class="etag">{d}</span>' for d in r["diagnoses"]]), unsafe_allow_html=True)
                            if r.get("lab_values"):
                                lab_data = {l["test"]: f"{l['value']} {l.get('unit','')}" for l in r["lab_values"] if l.get("value")}
                                st.json(lab_data)
            else:
                st.error(f"API error: {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("Cannot reach MedSight API — is the backend running?")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: About
# ══════════════════════════════════════════════════════════════════════════════
elif page == "About":
    st.markdown("""
    <div class="page-eyebrow">About</div>
    <div class="page-title">MedSight</div>
    <div class="page-sub">Privacy-preserving clinical intelligence for Indian healthcare settings.</div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="scard">
      <div class="scard-label">Mission</div>
      <div class="scard-body">
        Clinicians in under-resourced Indian hospitals spend significant time manually reviewing complex lab reports
        without specialist support. MedSight automates risk identification, trend tracking, and plain-language summarization —
        with no data ever leaving the device.
      </div>
    </div>
    """, unsafe_allow_html=True)

    feats = [
        ("🔒", "Fully Offline", "All inference runs locally. Patient data never reaches any server — critical for clinical data compliance."),
        ("📈", "Longitudinal Tracking", "Detects worsening trends across multiple visits, not just single-point anomalies. Clinically far more meaningful."),
        ("🇮🇳", "Indian Healthcare Context", "Risk flagging uses ICMR reference ranges, not Western defaults. Supports Hindi/English mixed reports via EasyOCR."),
        ("💡", "Explainable Flags", "Every risk shows the violated ICMR guideline, clinical reasoning chain, and specific recommended action."),
    ]
    fc = st.columns(2)
    for i, (icon, title, desc) in enumerate(feats):
        with fc[i % 2]:
            st.markdown(f"""
            <div class="scard" style="margin-bottom:10px;">
              <div style="font-size:22px;margin-bottom:8px;">{icon}</div>
              <div style="font-size:13px;font-weight:600;color:#94AFCF;margin-bottom:6px;">{title}</div>
              <div class="scard-body" style="font-size:12px;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="sec-head">Tech Stack</div>', unsafe_allow_html=True)
    stack = ["GLiNER", "Phi-3 Mini 4-bit", "ChromaDB", "EasyOCR", "PyMuPDF", "FastAPI", "Streamlit", "Docker", "ICMR Reference Ranges", "indic-transliteration"]
    st.markdown(" ".join([f'<span class="etag">{s}</span>' for s in stack]), unsafe_allow_html=True)
