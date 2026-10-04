"""
scripts/generate_architecture_diagram.py
Generates the official system architecture diagram PNG for the
CIBC Collections Intelligence Platform using Pillow.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "docs" / "architecture"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "cibc_collections_architecture.png"

def draw_rounded_rect(draw, xy, corner_radius, fill, outline=None, width=1):
    x0, y0, x1, y1 = xy
    r = corner_radius
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.pieslice([x0, y0, x0 + 2*r, y0 + 2*r], 180, 270, fill=fill)
    draw.pieslice([x1 - 2*r, y0, x1, y0 + 2*r], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2*r, x0 + 2*r, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2*r, y1 - 2*r, x1, y1], 0, 90, fill=fill)
    if outline:
        draw.line([x0 + r, y0, x1 - r, y0], fill=outline, width=width)
        draw.line([x0 + r, y1, x1 - r, y1], fill=outline, width=width)
        draw.line([x0, y0 + r, x0, y1 - r], fill=outline, width=width)
        draw.line([x1, y0 + r, x1, y1 - r], fill=outline, width=width)
        draw.arc([x0, y0, x0 + 2*r, y0 + 2*r], 180, 270, fill=outline, width=width)
        draw.arc([x1 - 2*r, y0, x1, y0 + 2*r], 270, 360, fill=outline, width=width)
        draw.arc([x0, y1 - 2*r, x0 + 2*r, y1], 90, 180, fill=outline, width=width)
        draw.arc([x1 - 2*r, y1 - 2*r, x1, y1], 0, 90, fill=outline, width=width)

def generate_diagram():
    w, h = 2600, 1500
    img = Image.new("RGB", (w, h), "#0F172A") # Slate 900 background
    draw = ImageDraw.Draw(img)

    # Header
    draw.text((80, 50), "CIBC Collections Intelligence Platform — System Architecture", fill="#FFFFFF")
    draw.text((80, 85), "Governed, Explainable & Fair Collections Architecture Across 4 Technical Layers | Grounded on 68M Records (Maple Bank)", fill="#94A3B8")

    # Layer 1: Data Product Factory
    draw_rounded_rect(draw, (80, 140, 680, 1380), 16, "#1E293B", "#334155", 2)
    draw.text((110, 170), "LAYER 1: DATA PRODUCT FACTORY", fill="#38BDF8")
    
    # 5 Source Systems
    sources = [
        ("CRM (1.02M Custs)", "crm_customer_id, PII, Profile"),
        ("Cards (660k Accounts)", "card_account_id, src_cust_ref"),
        ("Lending (404k Loans)", "loan_id, borrower_number"),
        ("Core Banking (780k Dep)", "deposit_account_id, 10-digit CIF"),
        ("Collections (367k Cases)", "case_id, coll_customer_ref")
    ]
    y_s = 220
    for s_title, s_desc in sources:
        draw_rounded_rect(draw, (110, y_s, 650, y_s + 75), 10, "#0F172A", "#475569", 1)
        draw.text((130, y_s + 15), s_title, fill="#F8FAFC")
        draw.text((130, y_s + 42), s_desc, fill="#94A3B8")
        y_s += 90

    # Entity Resolution Block
    draw_rounded_rect(draw, (110, 690, 650, 850), 12, "#1E3A8A", "#60A5FA", 2)
    draw.text((130, 710), "ENTITY RESOLUTION ENGINE", fill="#93C5FD")
    draw.text((130, 740), "- Deterministic Matching (Phone/Email/DOB = 1.0)", fill="#FFFFFF")
    draw.text((130, 770), "- Probabilistic Matching (Jaro-Winkler >= 0.92)", fill="#FFFFFF")
    draw.text((130, 800), "- Review Queue for Confidence < 0.85 (10,365 records)", fill="#FCA5A5")

    # Golden Financial ID
    draw_rounded_rect(draw, (110, 875, 650, 975), 12, "#047857", "#34D399", 2)
    draw.text((130, 895), "GOLDEN FINANCIAL ID (GID-XXXXXXX)", fill="#A7F3D0")
    draw.text((130, 930), "1,001,879 Unique Borrower Identities Resolved", fill="#FFFFFF")

    # DuckDB & Data Contract
    draw_rounded_rect(draw, (110, 1000, 650, 1170), 10, "#0F172A", "#475569", 1)
    draw.text((130, 1020), "Vectorized Analytical Lakehouse", fill="#E2E8F0")
    draw.text((130, 1055), "DuckDB In-Process Engine (68,162,322 records)", fill="#94A3B8")
    draw.text((130, 1085), "18 Automated DQ Rules (0 critical defects)", fill="#34D399")
    draw.text((130, 1115), "ODCS v3.0.0 Data Contract (DC-COLL-360)", fill="#38BDF8")

    # Golden Customer 360
    draw_rounded_rect(draw, (110, 1195, 650, 1345), 12, "#4338CA", "#818CF8", 2)
    draw.text((130, 1215), "GOLDEN CUSTOMER 360", fill="#C7D2FE")
    draw.text((130, 1250), "Single Governed Table (golden_customer_360)", fill="#FFFFFF")
    draw.text((130, 1280), "Zero Protected Attributes | Full Lineage Traceability", fill="#A5B4FC")
    draw.text((130, 1310), "Parquet Lakehouse Export (1,001,879 rows in 8.4s)", fill="#FFFFFF")

    # Layer 2: Insight & NLP
    draw_rounded_rect(draw, (720, 140, 1320, 730), 16, "#1E293B", "#334155", 2)
    draw.text((750, 170), "LAYER 2: INSIGHT & NLP PLATFORM", fill="#38BDF8")

    draw_rounded_rect(draw, (750, 220, 1290, 370), 12, "#0F172A", "#475569", 1)
    draw.text((770, 245), "Natural Language to SQL Engine", fill="#F8FAFC")
    draw.text((770, 280), "- Translates supervisor / agent queries to DuckDB SQL", fill="#CBD5E1")
    draw.text((770, 310), "- Always displays executed SQL alongside query results", fill="#34D399")
    draw.text((770, 335), "- Evaluated on 35 Official Benchmark Scenarios", fill="#38BDF8")

    draw_rounded_rect(draw, (750, 395, 1290, 545), 12, "#7F1D1D", "#F87171", 2)
    draw.text((770, 420), "Refusal & Privacy Guardrails", fill="#FECACA")
    draw.text((770, 455), "- Refuses Out-of-Scope queries (BQ-018: Weather)", fill="#FFFFFF")
    draw.text((770, 485), "- Refuses Bulk PII Exfiltration (BQ-023: Ontario list)", fill="#FFFFFF")
    draw.text((770, 515), "- Refuses Protected Attributes (BQ-029/031: Gender/FSA)", fill="#FFFFFF")

    draw_rounded_rect(draw, (750, 570, 1290, 700), 12, "#0F172A", "#475569", 1)
    draw.text((770, 595), "35 Benchmark Question Evaluation", fill="#F8FAFC")
    draw.text((770, 630), "100% Benchmark Coverage (Dev + Test Splits)", fill="#34D399")
    draw.text((770, 660), "BQ-035 Open Cases by Bucket: Exact Integer Match", fill="#38BDF8")

    # Layer 3: Feature Store & Collection Memory
    draw_rounded_rect(draw, (720, 760, 1320, 1380), 16, "#1E293B", "#334155", 2)
    draw.text((750, 790), "LAYER 3: COLLECTION MEMORY & FEATURES", fill="#38BDF8")

    draw_rounded_rect(draw, (750, 840, 1290, 990), 12, "#0F172A", "#475569", 1)
    draw.text((770, 865), "Longitudinal Collection Memory", fill="#F8FAFC")
    draw.text((770, 900), "- 3,581,511 Historical Interactions & PTPs", fill="#CBD5E1")
    draw.text((770, 930), "- NLP Hardship Detection: 84,289 notes flagged", fill="#F59E0B")
    draw.text((770, 955), "- Solves the Five Golden Questions instantly", fill="#38BDF8")

    draw_rounded_rect(draw, (750, 1015, 1290, 1350), 12, "#1E3A8A", "#60A5FA", 2)
    draw.text((770, 1040), "3-Branch Financial Health Engine", fill="#93C5FD")
    draw.text((770, 1075), "Branch A — Exposure Analysis (DTI Ratio)", fill="#FFFFFF")
    draw.text((770, 1105), "Branch B — Cash-Flow Stress (Liquidity & Lag)", fill="#FFFFFF")
    draw.text((770, 1135), "Branch C — Payment Behaviour (PTP Rate & DPD)", fill="#FFFFFF")
    draw.text((770, 1175), "Debt Service Ratio (DSR) & Affordability Assessment", fill="#34D399")
    draw.text((770, 1210), "1,001,879 Customers Scored in 0.96s (DuckDB SQL)", fill="#FFFFFF")
    draw.text((770, 1245), "Composite: GOOD (895k) | FAIR (45k) | STRESSED (43k) | CRITICAL (19k)", fill="#94A3B8")
    draw.text((770, 1285), "Can Support Arrangement: YES / MARGINAL / NO", fill="#A7F3D0")

    # Layer 4: AI Decisioning & Frontline Cockpit
    draw_rounded_rect(draw, (1360, 140, 2520, 1380), 16, "#1E293B", "#334155", 2)
    draw.text((1390, 170), "LAYER 4: AI DECISIONING & AGENT ASSIST COCKPIT", fill="#38BDF8")

    # Next Best Action
    draw_rounded_rect(draw, (1390, 220, 2490, 520), 12, "#047857", "#34D399", 2)
    draw.text((1420, 245), "POLICY-CONSTRAINED NEXT BEST ACTION (NBA)", fill="#A7F3D0")
    draw.text((1420, 280), "93,240 Active Delinquency Recommendations Evaluated in 0.88s", fill="#FFFFFF")
    draw.text((1420, 315), "Rule 1: Hardship / Vulnerability -> Specialist Review (Protection)", fill="#FEF08A")
    draw.text((1420, 350), "Rule 2: DPD > 90 -> Senior Escalation & Review", fill="#FFFFFF")
    draw.text((1420, 385), "Rule 3: Sustainability Gate (Cannot pay) -> Hardship Assistance", fill="#FFFFFF")
    draw.text((1420, 420), "Rule 4: Marginal Financial Capacity -> Structured Payment Plan", fill="#FFFFFF")
    draw.text((1420, 455), "Rule 5: Early Stage (<=30 DPD) + Healthy -> Automated Digital Reminder", fill="#FFFFFF")
    draw.text((1420, 485), "Distribution: HUMAN_REVIEW: 58.5k | REMINDER: 20.9k | PAYMENT_PLAN: 13.8k", fill="#A7F3D0")

    # Cockpit UI
    draw_rounded_rect(draw, (1390, 545, 2490, 1170), 12, "#0F172A", "#475569", 2)
    draw.text((1420, 575), "Agent Assist Cockpit (Streamlit Interface)", fill="#F8FAFC")

    # Cockpit Sub-panels
    panels = [
        ("Panel 1: Golden Financial ID & Customer 360", "Resolved borrower name, primary contact, cross-product exposure, delinquency history."),
        ("Panel 2: Financial Health Traffic Lights", "Real-time visual badges: Exposure (Low/Med/High), Cashflow, Payment Behaviour, Composite Health."),
        ("Panel 3: Collection Memory & Five Golden Questions", "Timestamped interaction timeline, PTP records, previous promises kept/broken, agent notes."),
        ("Panel 4: Policy-Constrained Recommendation", "Recommended action, plain-English explanation, factual evidence tags, cited policy rule."),
        ("Panel 5: Human-in-the-Loop Controls", "Frontline agent control: Accept, Modify, or Override recommendation with mandatory audit reasoning."),
        ("Panel 6: Smart Payment Plan Formulator", "3 affordability-tested plan options (Fast-Track, Balanced, Step-Up) calculated from monthly surplus."),
        ("Panel 7: Grounded Natural Language Query", "Ad-hoc portfolio exploration with verified DuckDB SQL generation and table visualization.")
    ]
    y_p = 620
    for p_name, p_desc in panels:
        draw_rounded_rect(draw, (1420, y_p, 2460, y_p + 65), 8, "#1E293B", "#334155", 1)
        draw.text((1440, y_p + 12), p_name, fill="#38BDF8")
        draw.text((1440, y_p + 36), p_desc, fill="#CBD5E1")
        y_p += 76

    # Governance Bar
    draw_rounded_rect(draw, (1390, 1195, 2490, 1345), 12, "#1E3A8A", "#60A5FA", 2)
    draw.text((1420, 1215), "CROSS-CUTTING GOVERNANCE, AUDITABILITY & FAIRNESS", fill="#93C5FD")
    draw.text((1420, 1250), "Zero Protected Attributes in Decision Models | Full Audit Trail Logging | Human Override Rights", fill="#FFFFFF")
    draw.text((1420, 1280), "Deterministic Math (LLM is Never Calculator of Record) | CASL & Canadian Regulatory Compliance", fill="#A7F3D0")
    draw.text((1420, 1310), "Production Performance: End-to-End Execution of 68M Records in Under 70 Seconds", fill="#FFFFFF")

    img.save(str(OUT_FILE))
    print(f"Architecture diagram saved to: {OUT_FILE}")

if __name__ == "__main__":
    generate_diagram()
