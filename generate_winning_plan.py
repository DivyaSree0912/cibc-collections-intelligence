from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ─── helpers ──────────────────────────────────────────────────────────────────

def shade_cell(cell, fill_hex):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)

def rgb(hex6):
    return RGBColor(*[int(hex6[i:i+2], 16) for i in (0, 2, 4)])

def heading(doc, text, level=1, color='1E3A5F'):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt({1:20,2:14,3:12,4:11}.get(level,11))
    run.font.color.rgb = rgb(color)
    p.paragraph_format.space_before = Pt({1:16,2:12,3:8,4:6}.get(level,6))
    p.paragraph_format.space_after  = Pt(4)
    return p

def para(doc, text, bold=False, italic=False, size=10.5, color='2D3748',
         align=WD_ALIGN_PARAGRAPH.LEFT, sb=2, sa=5):
    p = doc.add_paragraph()
    p.alignment = align
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    r.font.size = Pt(size)
    r.font.color.rgb = rgb(color)
    p.paragraph_format.space_before = Pt(sb)
    p.paragraph_format.space_after  = Pt(sa)
    return p

def bullet(doc, text, prefix=None, prefix_color='1E3A5F', color='374151', indent=0.2):
    p = doc.add_paragraph(style='List Bullet')
    if prefix:
        rb = p.add_run(prefix)
        rb.bold = True; rb.font.size = Pt(10)
        rb.font.color.rgb = rgb(prefix_color)
    r = p.add_run(text)
    r.font.size = Pt(10)
    r.font.color.rgb = rgb(color)
    p.paragraph_format.left_indent = Inches(indent)
    p.paragraph_format.space_after  = Pt(2)

def divider(doc, color='2563EB'):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    b = OxmlElement('w:bottom')
    b.set(qn('w:val'), 'single')
    b.set(qn('w:sz'), '6')
    b.set(qn('w:space'), '1')
    b.set(qn('w:color'), color)
    pBdr.append(b)
    pPr.append(pBdr)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(8)

def callout(doc, label, text, bg='EFF6FF', bar='2563EB', lc='1D4ED8'):
    tbl = doc.add_table(rows=1, cols=2)
    tbl.columns[0].width = Cm(0.45)
    tbl.columns[1].width = Cm(15.55)
    shade_cell(tbl.cell(0,0), bar)
    shade_cell(tbl.cell(0,1), bg)
    p = tbl.cell(0,1).paragraphs[0]
    rb = p.add_run(label + '  ')
    rb.bold = True; rb.font.size = Pt(9); rb.font.color.rgb = rgb(lc)
    rt = p.add_run(text)
    rt.font.size = Pt(9.5); rt.font.color.rgb = rgb('374151')
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    p.paragraph_format.left_indent  = Inches(0.08)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent  = Inches(0.25)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after  = Pt(5)
    r = p.add_run(text)
    r.font.name = 'Courier New'; r.font.size = Pt(8.5)
    r.font.color.rgb = rgb('1E3A5F')
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'),'clear'); shd.set(qn('w:color'),'auto')
    shd.set(qn('w:fill'),'EEF2FF')
    pPr.append(shd)
    return p

def table(doc, headers, rows, hbg='1E3A5F', alt=('F0F9FF','FAFAFA')):
    t = doc.add_table(rows=len(rows)+1, cols=len(headers))
    t.style = 'Table Grid'
    for i,h in enumerate(headers):
        c = t.cell(0,i); shade_cell(c, hbg)
        r = c.paragraphs[0].add_run(h)
        r.bold=True; r.font.size=Pt(9.5); r.font.color.rgb=rgb('FFFFFF')
    for ri,row in enumerate(rows,1):
        for ci,val in enumerate(row):
            c = t.cell(ri,ci)
            shade_cell(c, alt[ri%2])
            r = c.paragraphs[0].add_run(str(val))
            r.bold = (ci==0); r.font.size = Pt(9.5)
            r.font.color.rgb = rgb('1E3A5F') if ci==0 else rgb('374151')
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t

def two_col_box(doc, left_title, left_items, right_title, right_items,
                lbg='EFF6FF', rbg='F0FDF4', lbar='2563EB', rbar='059669'):
    """Two side-by-side member boxes."""
    tbl = doc.add_table(rows=1, cols=2)
    tbl.style = 'Table Grid'
    tbl.columns[0].width = Cm(8.2)
    tbl.columns[1].width = Cm(8.2)
    for ci, (title, items, bg, bar) in enumerate(
            [(left_title, left_items, lbg, lbar),
             (right_title, right_items, rbg, rbar)]):
        cell = tbl.cell(0, ci)
        shade_cell(cell, bg)
        # title row
        tp = cell.paragraphs[0]
        tr = tp.add_run(title)
        tr.bold = True; tr.font.size = Pt(11)
        tr.font.color.rgb = rgb(bar)
        tp.paragraph_format.space_after = Pt(4)
        for item in items:
            ip = cell.add_paragraph()
            ir = ip.add_run('  • ' + item)
            ir.font.size = Pt(9.5); ir.font.color.rgb = rgb('374151')
            ip.paragraph_format.space_after = Pt(2)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

# ─── document ─────────────────────────────────────────────────────────────────

doc = Document()
sec = doc.sections[0]
sec.top_margin=Cm(2); sec.bottom_margin=Cm(2)
sec.left_margin=Cm(2.5); sec.right_margin=Cm(2)
doc.styles['Normal'].font.name = 'Calibri'
doc.styles['Normal'].font.size = Pt(10.5)

# ══════════════════════════════════════════════════════════════════════════════
# COVER
# ══════════════════════════════════════════════════════════════════════════════

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Collections Intelligence Platform')
r.bold=True; r.font.size=Pt(26); r.font.color.rgb=rgb('1E3A5F')
p.paragraph_format.space_before=Pt(6); p.paragraph_format.space_after=Pt(4)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Complete 2-Member Execution Blueprint  |  Top-50 Hackathon Edition')
r.italic=True; r.font.size=Pt(13); r.font.color.rgb=rgb('2563EB')
p.paragraph_format.space_after=Pt(3)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Golden Financial ID  |  Collection Memory  |  Financial Health Engine  |  Fair Collections  |  AI Decisioning')
r.font.size=Pt(9.5); r.font.color.rgb=rgb('6B7280')
p.paragraph_format.space_after=Pt(14)

divider(doc)

# ══════════════════════════════════════════════════════════════════════════════
# WHY YOU ARE TOP 50 — WHAT MAKES THIS PLAN WINNING
# ══════════════════════════════════════════════════════════════════════════════

heading(doc, '1.  Why You Are in the Top 50 — and What Wins from Here', level=1)

para(doc,
    'You have been shortlisted because your solution does something the other 49 teams almost certainly '
    'do not: it proposes an entirely new conceptual layer — the Golden Financial ID — that transforms '
    '"One customer, one ID" from a database join into a persistent financial identity infrastructure. '
    'The judges already recognise this is different. Now the task is to BUILD IT and PROVE IT.', color='374151')

callout(doc,
    'THE WINNING FORMULA: ',
    'The judges score 30% on Technical Quality + Working Demo. '
    'That is the single biggest prize. A working, integrated demo that shows: '
    'NL query -> Golden C360 -> Collection Memory -> Financial Health -> NBA -> Agent Cockpit '
    '— end-to-end in under 5 minutes — will dominate the room.',
    bg='FEF9C3', bar='CA8A04', lc='78350F')

para(doc, 'The five judging criteria and how your solution leads on every one:', color='374151')

table(doc,
    headers=['Criterion', 'Weight', 'Your Winning Edge'],
    rows=[
        ('Business Understanding', '20%', 'You address the exact pain point the brief describes: fragmented data, blind agents, unfair recovery. You name it precisely.'),
        ('Technical Quality & Working Demo', '30%', 'End-to-end working pipeline: raw CSV -> Golden ID -> NL query -> Agent Cockpit -> NBA. No other team will show this full chain.'),
        ('Innovative Ideas', '15%', 'Golden Financial ID is a novel architectural concept. Collection Memory is a named, structured innovation. Fair Collections is a principled framework.'),
        ('Teamwork', '15%', 'Clean split: Member 1 = data + identity + health engine. Member 2 = NLP + decisioning + demo. Each output feeds the other. Visible collaboration.'),
        ('Presentation & Storytelling', '20%', '"From data silos to Golden ID to fair decision" is a memorable, emotional arc. The Five Golden Questions and Customer A vs B contrast are judge-ready moments.'),
    ],
    hbg='1E3A5F'
)

divider(doc)

# ══════════════════════════════════════════════════════════════════════════════
# FULL SYSTEM DESIGN WORKFLOW — THE DOCUMENT EXPLAINED
# ══════════════════════════════════════════════════════════════════════════════

heading(doc, '2.  The Full System Design Workflow (from Your Document)', level=1)

para(doc,
    'The document defines an end-to-end flow across three hackathon layers plus a cross-cutting '
    'governance layer. Every component below must be built or demonstrated:', color='374151')

code(doc,
    "  BANK DATA SOURCES  (9 synthetic CSVs: customers, cards, loans, deposits,\n"
    "                       collections_cases, contact_history, agent_notes,\n"
    "                       call_transcripts, external bureau)\n"
    "          |\n"
    "          v\n"
    "  ===================== LAYER 1: DATA PRODUCT FACTORY =====================\n"
    "   Step 1: Raw Ingestion -> Bronze Layer (9 tables loaded as-is)\n"
    "   Step 2: Curate & Clean -> Silver Layer (normalised, typed, deduplicated)\n"
    "   Step 3: ENTITY RESOLUTION -> Golden Financial ID (GID-XXXXXX)\n"
    "            [Deterministic: phone/tax-ID match]\n"
    "            [Probabilistic: name fuzzy match, address tokens]\n"
    "            [Confidence Score per link]\n"
    "   Step 4: Golden C360 -> Master entity table keyed on GID\n"
    "            [Profile | Loans | Cards | Deposits | Collections | Income]\n"
    "   Step 5: Data Contract YAML + Quality Scorecard\n"
    "          |\n"
    "          v  [HANDOFF: golden_customer_360.csv + financial_health_features.csv]\n"
    "          |\n"
    "   Step 6: FINANCIAL HEALTH ENGINE\n"
    "            Branch A: Exposure Analysis  (total debt burden per GID)\n"
    "            Branch B: Cash-Flow Stress   (payroll disruption signals)\n"
    "            Branch C: Payment Behaviour  (PTP fulfillment rate, DPD velocity)\n"
    "            -> Composite Financial Health Score per GID\n"
    "            -> Affordability / DSR calculation\n"
    "          |\n"
    "          v\n"
    "  =================== LAYER 2: INSIGHT & NLP PLATFORM ====================\n"
    "   Step 7: Semantic Layer (human alias map for all column names)\n"
    "   Step 8: NL-to-SQL Engine (LLM converts plain English -> SQL -> result)\n"
    "            [Show SQL + source table for every answer]\n"
    "            [Editable search tokens]\n"
    "            [Refuse protected-attribute queries]\n"
    "   Step 9: Collection Memory RAG\n"
    "            [Chunk + embed agent_notes + call_transcripts]\n"
    "            [Semantic search per GID -> Five Golden Questions view]\n"
    "          |\n"
    "          v\n"
    "  ==================== LAYER 3: AI DECISIONING ENGINE ====================\n"
    "   Step 10: Next Best Action (NBA) Recommender\n"
    "             [Input: Financial Health + Collection Memory + Contact History]\n"
    "             [Output: Channel + Timing + Treatment + Explanation]\n"
    "   Step 11: Smart Payment Plan Generator\n"
    "             [Input: DSR + Exposure + PTP history]\n"
    "             [Output: 3 explainable plan options for human review]\n"
    "   Step 12: Agent Assist Cockpit (Streamlit UI)\n"
    "             [Displays: GID summary | Collection Memory | Health | NBA | Plans]\n"
    "   Step 13: Post-Call Summary Generator\n"
    "             [Input: call transcript] [Output: structured note via LLM]\n"
    "          |\n"
    "          v\n"
    "  ====================== GOVERNANCE (EVERY LAYER) ========================\n"
    "   - Data Contract with quality rules\n"
    "   - No protected attributes in any model\n"
    "   - Human-in-the-loop: NBA and Plans require agent approval\n"
    "   - Explainability: every recommendation shows its top factors\n"
    "          |\n"
    "          v\n"
    "  ========================= SUBMISSION PACKAGE ===========================\n"
    "   Code repository (GitHub) | Architecture diagram | Data Contract file\n"
    "   5-minute demo video | 10-slide pitch deck")

divider(doc)

# ══════════════════════════════════════════════════════════════════════════════
# THE SPLIT — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════

heading(doc, '3.  The 2-Member Split — Strategic Overview', level=1)

para(doc,
    'The workflow above maps cleanly onto two self-contained tracks with one formal handoff point. '
    'Member 1 builds the DATA FOUNDATION. Member 2 builds the INTELLIGENCE LAYER on top of it. '
    'Both members demo together.', color='374151')

code(doc,
    "  MEMBER 1 — TRACK: DATA FOUNDATION & IDENTITY                 (Steps 1-6)\n"
    "  ===========================================================================\n"
    "  Owns: Layer 1 entirely + Financial Health Engine backend\n"
    "  Primary Output: golden_customer_360.csv  +  financial_health_features.csv\n"
    "  Innovation owned: Golden Financial ID\n\n"
    "                  [ HANDOFF FILES — produced by Member 1, consumed by Member 2 ]\n\n"
    "  MEMBER 2 — TRACK: INTELLIGENCE & DECISION LAYER              (Steps 7-13)\n"
    "  ===========================================================================\n"
    "  Owns: Layer 2 + Layer 3 + UI + Demo + Pitch Deck\n"
    "  Primary Output: Working Agent Assist Cockpit + NL Query Demo\n"
    "  Innovation owned: Collection Memory + Fair Collections + NBA")

two_col_box(doc,
    'MEMBER 1 — Data Foundation',
    [
        'Step 1-2: Ingest & clean all 9 CSVs',
        'Step 3:   Entity Resolution -> Golden ID',
        'Step 4:   Build Golden C360 master table',
        'Step 5:   Data Contract YAML + Quality SLA',
        'Step 6:   Financial Health Engine (all 3 branches)',
        'HANDOFF:  golden_customer_360.csv',
        'HANDOFF:  financial_health_features.csv',
        'HANDOFF:  Schema definition shared with M2',
    ],
    'MEMBER 2 — Intelligence Layer',
    [
        'Step 7-8: Semantic Layer + NL-to-SQL engine',
        'Step 9:   Collection Memory RAG pipeline',
        'Step 10:  NBA Recommender',
        'Step 11:  Smart Payment Plan generator',
        'Step 12:  Agent Assist Cockpit (Streamlit)',
        'Step 13:  Post-Call Summary (LLM)',
        'OUTPUT:   10-Slide Pitch Deck',
        'OUTPUT:   5-min Demo Video',
    ]
)

divider(doc)

# ══════════════════════════════════════════════════════════════════════════════
# MEMBER 1 — DETAILED EXECUTION PLAN
# ══════════════════════════════════════════════════════════════════════════════

heading(doc, '4.  MEMBER 1: Complete Execution Plan — Data Foundation & Golden ID', level=1, color='1D4ED8')

callout(doc,
    'MEMBER 1 NORTH STAR: ',
    'Produce the cleanest, most credible Golden Customer 360 dataset the judges have ever seen at a hackathon. '
    'Every decision you make should be explainable, documented, and reproducible. '
    'The Golden Financial ID is your flagship innovation — treat it like a product.',
    bg='EFF6FF', bar='2563EB', lc='1D4ED8')

# Step 1-2
heading(doc, 'TASK 1 — Raw Ingestion & Silver Layer (Layer 1, Steps 1-2)', level=2, color='1D4ED8')
para(doc, 'Goal: Load all 9 synthetic sources. Produce one clean, typed, documented table per source domain.', color='374151')

bullet(doc, 'Load: customers.csv, card_accounts.csv, loan_accounts.csv, deposit_accounts.csv, collections_cases.csv, contact_history.csv, agent_notes.txt, call_transcripts.json, external.csv (bureau scores).')
bullet(doc, 'Standardise phone numbers: strip country codes, normalise to 10-digit format. Log how many were malformed.')
bullet(doc, 'Standardise names: lowercase, strip extra whitespace, remove special characters.')
bullet(doc, 'Parse & validate dates: convert all date strings to ISO-8601. Flag nulls and outliers.')
bullet(doc, 'Produce silver_{source}.csv for all 9 tables with column definitions documented in a data dictionary.')
bullet(doc, 'Write a data quality report: null rates, duplicate rows, format violation counts, outlier flags per table.', color='059669', prefix='DELIVERABLE: ')

# Step 3
heading(doc, 'TASK 2 — Entity Resolution & Golden Financial ID (Step 3)', level=2, color='1D4ED8')
para(doc, 'Goal: Assign one GID-XXXXXX to every unique real-world customer across all 9 sources. This is the core innovation.', color='374151')

callout(doc,
    'APPROACH: ',
    'Run deterministic matching first (high precision). '
    'Then run probabilistic matching on remaining unmatched records. '
    'Anything below 0.85 confidence = flagged as "review required", not forcibly linked.',
    bg='EFF6FF', bar='2563EB', lc='1D4ED8')

bullet(doc, 'PASS 1 — Deterministic: exact match on normalised phone OR normalised email OR customer_id across tables. Assign GID immediately at confidence = 1.0.')
bullet(doc, 'PASS 2 — Probabilistic: for unmatched records, compute Jaro-Winkler similarity on (name, address). Score >= 0.92 = auto-link. Score 0.85–0.91 = link with flag.')
bullet(doc, 'Assign GID-XXXXXX (sequential 6-digit, zero-padded) to each resolved entity cluster.')
bullet(doc, 'Record: how many source records per GID, which tables contributed, confidence score for each link.')
bullet(doc, 'Build entity_resolution_report.csv: GID, contributing_source_records, match_confidence, match_method, flagged_for_review.')
bullet(doc, 'Entity Resolution Report showing: total GIDs created, average confidence, % records resolved, unmatched count.', color='059669', prefix='DELIVERABLE: ')

# Step 4
heading(doc, 'TASK 3 — Golden Customer 360 Master Table (Step 4)', level=2, color='1D4ED8')
para(doc, 'Goal: Build golden_customer_360.csv — the master product table keyed on GID. This is what Member 2 queries.', color='374151')

bullet(doc, 'GID as primary key. One row per resolved customer.')
bullet(doc, 'Aggregate from silver tables per GID:')
bullet(doc, '     resolved_customer_name, preferred_contact_phone, preferred_contact_email', indent=0.45)
bullet(doc, '     total_active_facilities_count (loans + cards)', indent=0.45)
bullet(doc, '     total_aggregate_exposure (sum of outstanding across all lines)', indent=0.45)
bullet(doc, '     total_monthly_emi_obligations (sum of all active EMI amounts)', indent=0.45)
bullet(doc, '     max_dpd_across_portfolio (worst DPD bucket in portfolio)', indent=0.45)
bullet(doc, '     card_utilization_pct (card outstanding / credit limit)', indent=0.45)
bullet(doc, '     estimated_monthly_inflow (3-month avg salary credits from deposits)', indent=0.45)
bullet(doc, '     ptp_count_total, ptp_fulfilled_count, ptp_fulfillment_rate_24m', indent=0.45)
bullet(doc, '     last_contact_date, last_contact_channel, last_contact_outcome', indent=0.45)
bullet(doc, '     match_confidence_score, lineage_last_updated', indent=0.45)
bullet(doc, 'Add lineage metadata per column: source_system, pipeline_run_timestamp.')
bullet(doc, 'Mark PII columns with classification tag (confidential_pii).')
bullet(doc, 'golden_customer_360.csv — share with Member 2 as soon as complete.', color='059669', prefix='HANDOFF FILE: ')

# Step 5
heading(doc, 'TASK 4 — Data Contract & Quality Scorecard (Step 5)', level=2, color='1D4ED8')
para(doc, 'Goal: Publish the formal ODCS Data Contract — a mandatory hackathon deliverable for Layer 1.', color='374151')

bullet(doc, 'Write collections_360_contract.yaml (already drafted — finalise with real field names from your CSV).')
bullet(doc, 'Quality rules to implement and verify:')
bullet(doc, '     Uniqueness: GID must be unique across all rows.', indent=0.45)
bullet(doc, '     Freshness: lineage_last_updated within 24 hours.', indent=0.45)
bullet(doc, '     Range: match_confidence_score >= 0.85.', indent=0.45)
bullet(doc, '     Positive: total_aggregate_exposure >= 0.', indent=0.45)
bullet(doc, '     Exclusion: no race, religion, caste, gender columns in any model input.', indent=0.45)
bullet(doc, 'Produce a 1-page Data Quality Scorecard (PASS/FAIL per rule, counts, % compliance).')
bullet(doc, 'collections_360_contract.yaml + quality_scorecard.pdf', color='059669', prefix='DELIVERABLE: ')

# Step 6
heading(doc, 'TASK 5 — Financial Health Engine (Step 6)', level=2, color='1D4ED8')
para(doc, 'Goal: Compute 3-branch financial health scores per GID and store as financial_health_features.csv.', color='374151')

bullet(doc, 'Branch A — Exposure Score: total_aggregate_exposure / (estimated_monthly_inflow * 12). Normalise to 0–1. Flag "SEVERE" if > 0.7.')
bullet(doc, 'Branch B — Cash-Flow Stress Index: detect if salary deposit is missing or >7 days late in last 3 months. Assign LOW / MODERATE / HIGH / SEVERE label.')
bullet(doc, 'Branch C — Payment Behaviour Score: ptp_fulfillment_rate_24m * 0.5 + (1 - dpd_velocity) * 0.5. Higher = more reliable.')
bullet(doc, 'Composite Financial Health Score: weighted average of the 3 branches (institution-configurable weights, default: 0.35 / 0.35 / 0.30).')
bullet(doc, 'Debt Service Ratio (DSR): total_monthly_emi_obligations / estimated_monthly_inflow. Classify: LOW (<35%), MODERATE (35–60%), HIGH (60–80%), SEVERE (>80%).')
bullet(doc, 'Vulnerability Hardship Flag: check agent_notes and call_transcripts for keywords: "medical", "hospital", "job loss", "bereavement", "unemployment". Set boolean flag.')
bullet(doc, 'financial_health_features.csv — share with Member 2 for NBA model.', color='059669', prefix='HANDOFF FILE: ')

# M1 tools
heading(doc, 'Member 1 — Tools & Libraries', level=2, color='1D4ED8')
table(doc,
    headers=['Task', 'Tool/Library', 'Why'],
    rows=[
        ('Data loading & cleaning', 'Python + pandas', 'Standard, fast, flexible'),
        ('Fuzzy name matching', 'rapidfuzz / jellyfish', 'Best Jaro-Winkler implementation in Python'),
        ('Entity resolution (advanced)', 'splink library', 'State-of-the-art probabilistic linkage — very impressive for judges'),
        ('SQL queries over data', 'DuckDB (in-process)', 'Fast SQL on CSV/Parquet without a server'),
        ('Health score computation', 'pandas + numpy', 'Vectorised, fast'),
        ('Keyword search in notes', 'Python re / nltk', 'Hardship flag detection'),
        ('Data Contract', 'YAML + VS Code / PyYAML', 'Write and validate YAML contract'),
        ('Quality report', 'great_expectations OR pandas assertions', 'Automated rule checking with pass/fail output'),
        ('Visualisations', 'plotly / seaborn', 'Confidence distribution, DPD heatmap, DSR chart'),
    ],
    hbg='1D4ED8'
)

# M1 deliverables
heading(doc, 'Member 1 — Final Deliverable Checklist', level=2, color='1D4ED8')
table(doc,
    headers=['#', 'Deliverable', 'Format', 'Feeds Into'],
    rows=[
        ('1', 'silver_{source}.csv (x9 cleaned tables)', 'CSV', 'Member 2 queries + Data Contract'),
        ('2', 'entity_resolution_report.csv', 'CSV', 'Pitch slide 3 — "One customer, one ID" proof'),
        ('3', 'golden_customer_360.csv', 'CSV', 'Member 2 NL-to-SQL + Agent Cockpit'),
        ('4', 'financial_health_features.csv', 'CSV', 'Member 2 NBA model + Smart Plans'),
        ('5', 'collections_360_contract.yaml', 'YAML', 'Mandatory hackathon submission'),
        ('6', 'quality_scorecard.md / PDF', 'PDF/MD', 'Layer 1 demo + Pitch slide 7'),
        ('7', 'Architecture diagram (Layer 1)', 'PNG/SVG', 'Pitch deck slide 7'),
        ('8', 'data_dictionary.csv', 'CSV', 'Judge inspection + Member 2 semantic map'),
    ],
    hbg='1D4ED8'
)

divider(doc)

# ══════════════════════════════════════════════════════════════════════════════
# MEMBER 2 — DETAILED EXECUTION PLAN
# ══════════════════════════════════════════════════════════════════════════════

heading(doc, '5.  MEMBER 2: Complete Execution Plan — Intelligence & Decision Layer', level=1, color='059669')

callout(doc,
    'MEMBER 2 NORTH STAR: ',
    'Build the most memorable, impactful 5-minute demo in the room. '
    'Every judge should walk away having seen something they have never seen before: '
    'an agent assistant that knows the customer\'s entire financial story before the call even starts. '
    'Make the demo emotional, not just technical.',
    bg='F0FDF4', bar='059669', lc='065F46')

# Step 7-8
heading(doc, 'TASK 1 — Semantic Layer & NL-to-SQL Engine (Steps 7-8)', level=2, color='059669')
para(doc, 'Goal: Allow a collections manager to ask a question in plain English and get a correct, transparent answer backed by SQL.', color='374151')

bullet(doc, 'Build semantic_map.json: a dictionary mapping every golden_customer_360 column to its human-friendly name and description. E.g., "max_dpd_across_portfolio" -> "Days Overdue (worst product)".')
bullet(doc, 'Integrate LLM (Gemini API recommended — you have access via Google): send user question + schema context -> receive SQL.')
bullet(doc, 'Execute generated SQL against the golden_customer_360.csv using DuckDB (shared with Member 1).')
bullet(doc, 'Always display: (a) the generated SQL, (b) the source table, (c) execution time. Never show results without showing the working.')
bullet(doc, 'Implement editable search tokens: parse the SQL WHERE clause into visible chips the user can click to edit.')
bullet(doc, 'Implement refusal guardrail: if the user asks about any protected attribute (race, religion, gender, age, caste), return a structured refusal message.')
bullet(doc, 'Prepare 5 benchmark demo questions and verify each returns a correct result with SQL shown:')
bullet(doc, '     Q1: "Which customers have overdue card debt above Rs. 30,000 and a cash-flow stress index of HIGH or SEVERE?"', indent=0.45)
bullet(doc, '     Q2: "Show me all customers with a DPD above 60 days and a PTP fulfilment rate below 50%."', indent=0.45)
bullet(doc, '     Q3: "Which customers have more than 2 active loan facilities and total exposure above Rs. 2 lakh?"', indent=0.45)
bullet(doc, '     Q4: "List customers with a debt service ratio above 70% sorted by total exposure descending."', indent=0.45)
bullet(doc, '     Q5: "Which customers have a vulnerability hardship flag and are still in active collections?"', indent=0.45)

# Step 9
heading(doc, 'TASK 2 — Collection Memory RAG Pipeline (Step 9)', level=2, color='059669')
para(doc, 'Goal: Build a semantic memory store over agent_notes.txt and call_transcripts.json keyed on GID. This powers the "Five Golden Questions" view.', color='374151')

bullet(doc, 'Chunk agent_notes: one chunk per note entry (already per contact). Add metadata: GID, contact_date, channel.')
bullet(doc, 'Chunk call_transcripts: split each transcript into 300-word overlapping windows. Add metadata: GID, call_date, call_duration.')
bullet(doc, 'Embed all chunks using Gemini Embedding API (text-embedding-004) or sentence-transformers (all-MiniLM-L6-v2 if offline).')
bullet(doc, 'Store in ChromaDB (local, persistent). Collection name: collection_memory.')
bullet(doc, 'For any given GID, retrieve top-5 most semantically relevant chunks.')
bullet(doc, 'Write a Collection Memory Synthesizer: given retrieved chunks, call LLM to generate structured answers to the Five Golden Questions:')
bullet(doc, '     Q1: What happened before? (most recent 3 contacts, outcomes, channels used)', indent=0.45)
bullet(doc, '     Q2: What is happening now? (latest DPD, open obligations, salary delay flag)', indent=0.45)
bullet(doc, '     Q3: What has worked? (channels that got a response, PTPs that were honoured)', indent=0.45)
bullet(doc, '     Q4: What has NOT worked? (channels ignored, broken promises, call abandonments)', indent=0.45)
bullet(doc, '     Q5: What should I consider next? (pull from NBA output — see Task 3)', indent=0.45)

# Step 10
heading(doc, 'TASK 3 — Next Best Action Recommender (Step 10)', level=2, color='059669')
para(doc, 'Goal: For every GID in collections, recommend the best Channel + Timing + Treatment. Make it explainable.', color='374151')

bullet(doc, 'Features from Member 1\'s financial_health_features.csv: composite_health_score, cash_flow_stress_index, dsr_category, ptp_fulfillment_rate_24m, vulnerability_hardship_flag.')
bullet(doc, 'Features from golden_customer_360.csv: max_dpd_across_portfolio, last_contact_channel, last_contact_outcome, total_aggregate_exposure.')
bullet(doc, 'CHANNEL recommendation rule engine:')
bullet(doc, '     WhatsApp: if last WhatsApp contact had outcome = "responded" OR if pick-up rate on calls < 30%.', indent=0.45)
bullet(doc, '     Human Call: if DPD > 60 OR vulnerability_hardship_flag = True OR broken PTP count > 2.', indent=0.45)
bullet(doc, '     SMS/Digital Nudge: if DPD < 30 AND health_score = LOW AND ptp_fulfillment > 70%.', indent=0.45)
bullet(doc, 'TIMING recommendation: analyse contact_history outcomes by day-of-week and hour. Recommend the hour bin with highest response rate for this customer\'s segment.')
bullet(doc, 'TREATMENT recommendation:')
bullet(doc, '     REMINDER: health_score = LOW, DPD < 30, no broken PTPs.', indent=0.45)
bullet(doc, '     PAYMENT PLAN: DSR > 60% OR cash_flow_stress = HIGH/SEVERE OR broken_ptp > 1.', indent=0.45)
bullet(doc, '     HARDSHIP DISCUSSION: vulnerability_hardship_flag = True OR DSR > 80%.', indent=0.45)
bullet(doc, '     SPECIALIST REVIEW: DPD > 90 AND all prior treatments failed.', indent=0.45)
bullet(doc, 'Show explanation: top 2 factors that drove the recommendation (e.g., "DSR = 74% suggests payment capacity is constrained. PTP history of 40% suggests plan offers are more effective than payment demands.").')
bullet(doc, 'Human-in-the-Loop: NBA output is advisory only. Agent sees "Accept / Modify / Override" buttons.')

# Step 11
heading(doc, 'TASK 4 — Smart Payment Plan Generator (Step 11)', level=2, color='059669')
para(doc, 'Goal: Generate 3 explainable, affordable payment plan options per customer when NBA recommends PAYMENT PLAN treatment.', color='374151')

bullet(doc, 'Input per GID: estimated_monthly_inflow, total_monthly_emi_obligations, max_dpd_across_portfolio, total_aggregate_exposure, overdue_amount (from collections_cases).')
bullet(doc, 'Compute available monthly surplus: estimated_monthly_inflow - total_monthly_emi_obligations.')
bullet(doc, 'Generate Option A: 3-month step-up plan. Month 1 = 30% of overdue, Month 2 = 35%, Month 3 = 35%. Check if surplus >= Month 1 instalment.')
bullet(doc, 'Generate Option B: 6-month standard plan. Equal monthly instalments = overdue_amount / 6. Check surplus.')
bullet(doc, 'Generate Option C: Full settlement with late-fee waiver (if customer can pay 90% of overdue immediately).')
bullet(doc, 'For each option: display instalment amount, duration, total cost, affordability signal (GREEN/AMBER/RED against surplus).')
bullet(doc, 'If surplus < minimum instalment of all 3 options: flag "Hardship Review Required" — do not generate a plan. Escalate to specialist.')
bullet(doc, 'CRITICAL: Label all plans as "For Agent Review Only — Not Auto-Applied". Human agent must select and confirm.')

# Step 12
heading(doc, 'TASK 5 — Agent Assist Cockpit UI (Step 12)', level=2, color='059669')
para(doc, 'Goal: A single-screen Streamlit application that combines everything into the agent\'s view. This IS the demo.', color='374151')

callout(doc,
    'DEMO IMPACT: ',
    'This is what the judges will see and remember. Make it clean, fast, and emotional. '
    'The moment an agent types a GID and instantly sees the customer\'s entire financial story '
    'is the demo\'s peak moment. Design for that moment.',
    bg='F0FDF4', bar='059669', lc='065F46')

bullet(doc, 'Input: Agent types or selects a GID from a dropdown of delinquent customers.')
bullet(doc, 'Section 1 — GOLDEN ID PROFILE: Customer name, GID, match confidence, active facilities, last contact.')
bullet(doc, 'Section 2 — FINANCIAL HEALTH DASHBOARD: Traffic light (GREEN/AMBER/RED) for DSR, Cash-Flow Stress, PTP Rate, Exposure. One number per indicator.')
bullet(doc, 'Section 3 — COLLECTION MEMORY (Five Golden Questions): LLM-generated structured answers, displayed as cards.')
bullet(doc, 'Section 4 — NEXT BEST ACTION: Channel recommendation, timing recommendation, treatment type, top 2 explanation factors. "Accept / Modify / Override" buttons.')
bullet(doc, 'Section 5 — SMART PAYMENT PLANS (if treatment = PAYMENT PLAN): 3 plan options with amounts, durations, and affordability indicators.')
bullet(doc, 'Section 6 — NL QUERY PANEL: Embedded NL-to-SQL widget. Agent can ask "What was this customer\'s last promise?" and get an instant SQL-backed answer.')
bullet(doc, 'Tech stack: Streamlit (Python). Deploy locally for demo. No external hosting needed.')

# Step 13
heading(doc, 'TASK 6 — Post-Call Summary & Pitch Deck (Step 13)', level=2, color='059669')

bullet(doc, 'Post-Call Summary: given a call_transcript, call Gemini API with prompt: "Extract: (1) reason for non-payment, (2) sentiment, (3) any promise made, (4) recommended follow-up action". Display as structured card.')
bullet(doc, '10-Slide Pitch Deck — own this entirely. Structure:')
bullet(doc, '     Slide 1: Title + team. Collections Intelligence Platform. "Unify the data. Remember the story. Recover fairly."', indent=0.45)
bullet(doc, '     Slide 2: The problem. Fragmented data. Blind agents. Unfair dunning. The 3 questions agents cannot answer today.', indent=0.45)
bullet(doc, '     Slide 3: Golden Financial ID — the innovation. Entity resolution diagram. "Not a database, an identity layer."', indent=0.45)
bullet(doc, '     Slide 4: Collection Memory — "Never start from zero." The 5 Golden Questions.', indent=0.45)
bullet(doc, '     Slide 5: Financial Health Engine — 3 branches. Customer A vs B contrast.', indent=0.45)
bullet(doc, '     Slide 6: Fair Collections + Smart Payment Plans. The north star principle.', indent=0.45)
bullet(doc, '     Slide 7: Full architecture diagram (all 3 layers). Clean, visual, with colour coding.', indent=0.45)
bullet(doc, '     Slide 8: Live demo screenshots. NL query. Agent cockpit. NBA. Payment plan.', indent=0.45)
bullet(doc, '     Slide 9: Governance — no protected attributes, human-in-the-loop, explainability.', indent=0.45)
bullet(doc, '     Slide 10: Impact metrics + evolution diagram. "FROM: data silos. TO: Golden ID -> fair outcome."', indent=0.45)

# M2 tools
heading(doc, 'Member 2 — Tools & Libraries', level=2, color='059669')
table(doc,
    headers=['Task', 'Tool/Library', 'Why'],
    rows=[
        ('LLM (NL-to-SQL, summaries)', 'Gemini API (google-generativeai)', 'Best quality, free tier, you have access'),
        ('Embedding model', 'Gemini text-embedding-004', 'State-of-the-art dense embeddings'),
        ('Vector store', 'ChromaDB (local persistent)', 'Simple, no server, fast retrieval'),
        ('SQL execution', 'DuckDB', 'Same as Member 1 — shared database file'),
        ('Agent UI', 'Streamlit', 'Build professional UI in pure Python, fast'),
        ('NBA rule engine', 'Python dict + pandas', 'Simple, transparent, no black-box ML needed'),
        ('Payment plan math', 'Python / numpy', 'Arithmetic on instalment amounts'),
        ('Presentation', 'Canva / Google Slides', 'Professional design, easy collaboration'),
    ],
    hbg='059669'
)

# M2 deliverables
heading(doc, 'Member 2 — Final Deliverable Checklist', level=2, color='059669')
table(doc,
    headers=['#', 'Deliverable', 'Format', 'Judges See'],
    rows=[
        ('1', 'NL-to-SQL Engine (working on 5 benchmark questions)', 'Python / Notebook', 'Layer 2 demo — transparent SQL shown'),
        ('2', 'Collection Memory Vector Store + 5-Question Synthesizer', 'ChromaDB + Python', 'Agent Cockpit Section 3'),
        ('3', 'NBA Recommender (channel + timing + treatment)', 'Python rule engine', 'Layer 3 — explainable recommendation'),
        ('4', 'Smart Payment Plan Generator (3 options per GID)', 'Python + pandas', 'Layer 3 — affordability-driven plans'),
        ('5', 'Agent Assist Cockpit (Streamlit app)', 'Streamlit Python', 'THE MAIN DEMO — 5-minute showcase'),
        ('6', 'Post-Call Summary Generator', 'Python + Gemini API', 'Layer 3 bonus — QA / compliance'),
        ('7', '10-Slide Pitch Deck', 'Google Slides / PPTX', '20% of judging score'),
        ('8', '5-Minute Demo Video', 'Screen recording', 'Hackathon mandatory submission'),
    ],
    hbg='059669'
)

divider(doc)

# ══════════════════════════════════════════════════════════════════════════════
# PARALLEL TIMELINE
# ══════════════════════════════════════════════════════════════════════════════

heading(doc, '6.  Parallel Build Timeline', level=1)

para(doc,
    'Both members start simultaneously. Member 2 works on NL-to-SQL and ChromaDB setup using a '
    'sample schema while Member 1 builds the full pipeline. No blocking at start.', color='374151')

table(doc,
    headers=['Stage', 'Member 1 Activity', 'Member 2 Activity', 'Sync Point'],
    rows=[
        ('START\n(Day 1)',
         'Set up project repo. Load all 9 CSVs. Explore schemas. Write data dictionary.',
         'Set up Gemini API. Write semantic_map.json on known schema. Test basic NL-to-SQL on sample data.',
         'Share repo structure + agreed column names'),
        ('BUILD A\n(Day 1-2)',
         'Build Silver cleaning scripts. Run Entity Resolution Pass 1 (deterministic). Generate first GIDs.',
         'Build ChromaDB pipeline. Embed agent_notes. Test Collection Memory retrieval on sample GID.',
         'Share first golden_customer_360_sample.csv (50 rows) so M2 can test full stack'),
        ('HANDOFF\n(Day 2)',
         'Produce FINAL golden_customer_360.csv + financial_health_features.csv. Share with M2.',
         'Build NBA rule engine on M1 sample data. Start Streamlit app structure.',
         'FORMAL HANDOFF: M1 shares final files. M2 switches to real data.'),
        ('BUILD B\n(Day 3)',
         'Write Data Contract YAML. Run quality checks. Produce scorecard. Build Layer 1 architecture diagram.',
         'Wire NBA + Payment Plans into Streamlit. Complete Agent Cockpit with all 6 sections. Add Post-Call Summary.',
         'Both members test the full end-to-end demo together'),
        ('POLISH\n(Day 4)',
         'Review M2 demo for data accuracy. Fix any data issues. Assist with pitch deck data slides.',
         'Polish Streamlit UI. Record 5-min demo video. Complete 10-slide pitch deck.',
         'Final walkthrough rehearsal together. Submission.'),
    ],
    hbg='1E3A5F'
)

divider(doc)

# ══════════════════════════════════════════════════════════════════════════════
# SHARED REPOSITORY STRUCTURE
# ══════════════════════════════════════════════════════════════════════════════

heading(doc, '7.  GitHub Repository Structure', level=1)

para(doc, 'Both members commit to the same GitHub repository. This structure is agreed from Day 1:', color='374151')

code(doc,
    "  collections-intelligence-platform/\n"
    "  |\n"
    "  |-- README.md                     <- Project overview + demo run instructions\n"
    "  |\n"
    "  |-- data/\n"
    "  |   |-- raw/                      <- M1: original CSVs from hackathon\n"
    "  |   |-- silver/                   <- M1: cleaned per-domain tables (x9)\n"
    "  |   |-- golden/\n"
    "  |       |-- golden_customer_360.csv       <- M1 HANDOFF FILE\n"
    "  |       |-- financial_health_features.csv <- M1 HANDOFF FILE\n"
    "  |       |-- entity_resolution_report.csv  <- M1 proof of Golden ID\n"
    "  |\n"
    "  |-- contracts/\n"
    "  |   |-- collections_360_contract.yaml     <- M1 mandatory deliverable\n"
    "  |   |-- quality_scorecard.md              <- M1 quality SLA\n"
    "  |   |-- data_dictionary.csv               <- M1 column definitions\n"
    "  |\n"
    "  |-- layer1_pipeline/              <- M1 Python scripts\n"
    "  |   |-- 01_ingest.py\n"
    "  |   |-- 02_silver_clean.py\n"
    "  |   |-- 03_entity_resolution.py\n"
    "  |   |-- 04_golden_c360.py\n"
    "  |   |-- 05_financial_health.py\n"
    "  |\n"
    "  |-- layer2_nlp/                   <- M2 Python scripts\n"
    "  |   |-- semantic_map.json\n"
    "  |   |-- nl_to_sql.py\n"
    "  |   |-- collection_memory_rag.py\n"
    "  |   |-- chroma_db/                <- vector store (gitignore large files)\n"
    "  |\n"
    "  |-- layer3_decisioning/           <- M2 Python scripts\n"
    "  |   |-- nba_recommender.py\n"
    "  |   |-- payment_plan_engine.py\n"
    "  |   |-- post_call_summary.py\n"
    "  |\n"
    "  |-- app/\n"
    "  |   |-- cockpit.py                <- M2 Streamlit Agent Assist Cockpit\n"
    "  |   |-- requirements.txt\n"
    "  |\n"
    "  |-- docs/\n"
    "      |-- architecture_diagram.png\n"
    "      |-- pitch_deck.pptx\n"
    "      |-- demo_script.md")

divider(doc)

# ══════════════════════════════════════════════════════════════════════════════
# THE DEMO SCRIPT
# ══════════════════════════════════════════════════════════════════════════════

heading(doc, '8.  The 5-Minute Demo Script (Win the Room)', level=1)

callout(doc,
    'STRATEGY: ',
    'Do not demo features. Demo a story. Walk the judge through ONE customer\'s journey from fragmented data to fair outcome.',
    bg='FEF9C3', bar='CA8A04', lc='78350F')

table(doc,
    headers=['Minute', 'What You Show', 'What the Judge Hears'],
    rows=[
        ('0:00 – 0:45',
         'Open a spreadsheet with 9 separate CSVs. "This is the bank\'s reality today. The same customer appears as 4 different records."',
         '"They actually understand the problem, not just the solution."'),
        ('0:45 – 1:30',
         'Run 03_entity_resolution.py live (or show pre-run output). "Our pipeline resolved 2,400 records into 843 unique Golden Financial IDs. Here is GID-000241."',
         '"That entity resolution report with confidence scores is real data engineering."'),
        ('1:30 – 2:30',
         'Open Agent Cockpit. Type GID-000241. Show all 6 sections appear instantly. Focus on Section 3 (Collection Memory). "The agent knows: this customer promised Rs. 12,000 on the 15th. It was broken. Medical reimbursement delay. WhatsApp at 6 PM is the only channel that works."',
         '"This is what every bank needs. The agent has the whole story before the call."'),
        ('2:30 – 3:15',
         'Show Section 2 — Financial Health. "DSR is 74%. Cash-flow stress is HIGH. This customer is not refusing to pay. They genuinely cannot right now." Show NBA: Treatment = PAYMENT PLAN.',
         '"Fair Collections. They distinguish willingness from ability. That is rare."'),
        ('3:15 – 4:00',
         'Show Section 5 — Smart Payment Plans. "Three options generated based on this customer\'s verified surplus of Rs. 8,200/month. Option A fits within that. Agent reviews, approves, sends WhatsApp payment link."',
         '"This is end-to-end. From data to action."'),
        ('4:00 – 4:30',
         'Switch to NL Query panel. Type: "Show all customers with DSR above 70% and a hardship flag." Result appears with SQL shown. "Any manager can query the data in plain English."',
         '"Layer 2 — working. Transparent."'),
        ('4:30 – 5:00',
         'Close with the evolution quote: "Traditional collections asks: How much does this customer owe? We help the agent ask: What is the right next step for this specific person today?"',
         '"This team has a philosophy, not just code."'),
    ],
    hbg='1E3A5F'
)

divider(doc)

# ══════════════════════════════════════════════════════════════════════════════
# WINNING DIFFERENTIATORS SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

heading(doc, '9.  Your 5 Winning Differentiators vs. All Other Top-50 Teams', level=1)

table(doc,
    headers=['#', 'Differentiator', 'What Most Teams Will Do', 'What You Will Do'],
    rows=[
        ('1', 'Golden Financial ID', 'Join customer tables on a common ID field.', 'Build a probabilistic entity resolution pipeline that assigns a confidence-scored GID. Named, principled, architectural.'),
        ('2', 'Collection Memory', 'Maybe show a chatbot over transcripts.', 'Build a structured Five-Golden-Questions view powered by RAG + LLM synthesis, tied to the customer\'s GID. Persistent cross-agent memory.'),
        ('3', 'Financial Health Engine', 'Show DPD buckets or a simple credit score.', 'Compute 3-branch exposure + cash-flow + behaviour composite score per GID. Affordability-driven, institution-configurable.'),
        ('4', 'Fair Collections principle', 'Focus on maximising recovery.', 'Explicitly build in hardship detection, payment plan affordability, and human-in-the-loop as design constraints, not afterthoughts.'),
        ('5', 'Integrated Working Demo', 'Show individual features separately.', 'Show one complete end-to-end flow: CSV -> Golden ID -> Agent Cockpit -> NBA -> Payment Plan -> NL Query. One story. One screen.'),
    ],
    hbg='1E3A5F'
)

divider(doc)

# ══════════════════════════════════════════════════════════════════════════════
# FINAL CLOSING
# ══════════════════════════════════════════════════════════════════════════════

heading(doc, '10.  The Goal You Are Building Towards', level=1)

para(doc,
    'Every line of code, every data pipeline, every UI component should serve one purpose: '
    'making the judge feel that your system is not a student project, but a real platform '
    'that a bank could deploy tomorrow.', color='374151', bold=False)

code(doc,
    "  THE EVOLUTION YOUR SOLUTION DEMONSTRATES:\n\n"
    "  FROM:\n"
    "    Data Silos  ->  Overdue Loan Record  ->  Rigid Dunning  ->  Aggressive Recovery\n\n"
    "  TO:\n"
    "    Golden Financial ID\n"
    "         ->  Customer 360  (governed, lineaged, live)\n"
    "              ->  Collection Memory  (never start from zero)\n"
    "                   ->  Financial Health  (capacity, not just debt)\n"
    "                        ->  Fair Decision Intelligence  (appropriate, explainable)\n"
    "                             ->  Human-Assisted Action  (agent empowered, not replaced)\n"
    "                                  ->  Customer Outcome  (sustainable, not extractive)\n"
    "                                       ->  Learning  (continuous feedback loop)\n\n"
    "  THIS IS WHAT WINS.")

callout(doc,
    'FINAL QUOTE FOR YOUR PITCH: ',
    '"We do not want the collection agent to ask: What does this loan record tell me?\n\n'
    'We want our system to help the agent ask:\n\n'
    'What does this customer\'s complete relevant financial context tell me, '
    'what has happened before, what is changing now, and what is the most appropriate next step?"',
    bg='EFF6FF', bar='2563EB', lc='1D4ED8')

# ─── save ─────────────────────────────────────────────────────────────────────

out = r'C:\Users\dadid\.gemini\antigravity\scratch\collections-ai\Winning_Execution_Plan_2Member.docx'
doc.save(out)
print(f'Saved -> {out}')
