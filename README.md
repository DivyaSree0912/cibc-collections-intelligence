# CIBC Collections Intelligence Platform
## Maple Bank — Governed Customer-State Collections Intelligence System

> **Hackathon:** CIBC Collections Hackathon — Build Phase  
> **Deadline:** 4 Oct 2026, 9:00 PM IST  
> **Dataset:** `nuxsh/maple-collections-hackathon` (HuggingFace) — 31 tables, 1M synthetic customers, Oct 2016–Sep 2026  
> **Team:** 2 members  

---

## What Changed from System Design Phase

| Area | Design Phase | Build Phase Decision | Reason |
|---|---|---|---|
| Identity resolution | Conceptual Golden Financial ID | Implemented as 5-source deterministic + probabilistic linker using Splink/DuckDB | Actual dataset has 5 source systems per Build Phase instructions |
| Feature store | Conceptual | Implemented as Parquet-backed governed feature store with lineage YAML | Dataset is large (31 tables); need efficient storage |
| NLP layer | LLM NL-to-SQL | Gemini API for NL→SQL + RAG over transcripts/notes | Paid APIs allowed; data is synthetic |
| UI | Streamlit cockpit | Streamlit Agent Assist Cockpit (6 panels) | Most reliable for interactive demo |

---

## Submission Artifacts & Deliverables

| Deliverable | Location | Description | Status |
|---|---|---|---|
| **1. Code Repository** | Root workspace | Fully runnable, tested pipeline + Streamlit UI | ✅ Complete |
| **2. Architecture Diagram** | `docs/architecture/cibc_collections_architecture.png` & `.pdf` | 4-layer architecture diagram with governance | ✅ Complete |
| **3. Data Contract** | `docs/contracts/golden_c360_contract.yaml` | ODCS v3.0.0 Golden C360 data contract (DC-COLL-360) | ✅ Complete |
| **4. Data Quality Report** | `docs/reports/data_quality_report.md` | 18 automated checks; quantified defect remediation | ✅ Complete |
| **5. Benchmark Answers** | `data/benchmark_answers.csv` | All 35 benchmark questions (dev + test) evaluated | ✅ Complete |
| **6. Demo Video Guide** | `docs/DEMO_VIDEO_SCRIPT.md` | Timestamped 4m45s turn-by-turn video walkthrough script | ✅ Complete |
| **7. Pitch Deck** | `docs/CIBC_Collections_Intelligence_Pitch_Deck.pdf` & `.docx` | 10-slide executive presentation deck | ✅ Complete |
| **8. Master Test Suite** | `tests/test_pipeline.py` | Pytest suite: 7/7 tests passed in 12.72s | ✅ Complete |

---

## Verified Benchmark Results

- **Coverage:** 35 of 35 benchmark questions evaluated (100% coverage).
- **Official Ground Truth:** Benchmark `BQ-035` open collections cases by delinquency bucket matches official benchmark ground-truth to the exact integer across all 7 buckets (`1-30: 33,639`, `31-60: 25,389`, `61-90: 16,312`, `91-120: 10,251`, `121-150: 6,184`, `151-180: 4,045`, `180+: 180`).
- **Refusal Guardrails:** Correctly identifies and declines `BQ-018` (out-of-scope weather), `BQ-023` (bulk PII export), `BQ-024` (FSA redlining), and `BQ-029` / `BQ-031` (protected attributes).
- **High-Throughput Analytical Performance:**
  - 68,162,322 raw records ingested into DuckDB in **32 seconds**.
  - 1,788,432 cross-source records unified into persistent Golden Financial IDs in **14.7 seconds**.
  - 1,001,879 customers scored across 3 financial health branches in **0.96 seconds**.
  - 93,240 active collections accounts evaluated with policy Next Best Actions in **0.88 seconds**.
  - Complete end-to-end pipeline execution from raw data to decisioning in **< 70 seconds**.

---

## Architecture: The Closed Loop

```
RAW SOURCES (31 tables, 5 source systems)
        ↓
DATA PRODUCT FACTORY
  [Ingest → Validate → Clean → Standardise → Deduplicate]
        ↓
IDENTITY RESOLUTION  [Deterministic → Probabilistic → Confidence Gate]
        ↓
GOLDEN FINANCIAL ID  [One governed ID per customer]
        ↓
CUSTOMER 360  [Latest financial state, lineage, timestamps]
        ↓
COLLECTION MEMORY  [Full chronological interaction history]
        ↓
INSIGHT / NLP LAYER  [NL→SQL + RAG over notes/transcripts, evidence-grounded]
        ↓
FINANCIAL ANALYSIS  [Exposure + DPD + Cash Flow + Payment Behaviour]
        ↓
FEATURE STORE  [Governed, versioned, lineaged derived features]
        ↓
FINANCIAL HEALTH ENGINE  [Affordability, sustainability signal]
        ↓
POLICY CONSTRAINTS  [Eligible actions, hardship gates, protected-attr exclusion]
        ↓
NEXT BEST ACTION  [Explainable, policy-constrained recommendation]
        ↓
HUMAN / AGENT REVIEW  [Material decisions require human control]
        ↓
CUSTOMER OUTCOME  [Recorded action]
        ↓
COLLECTION MEMORY UPDATE  [Outcome becomes new event — closes the loop]
        ↓
MONITORING + LEARNING  ↺  [Next decision uses updated state]

[GOVERNANCE SURROUNDS EVERY STAGE]
```

---

## How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Download dataset

```bash
python scripts/download_data.py
```

### 3. Run the full pipeline

```bash
python scripts/run_pipeline.py
```

### 4. Launch Agent Assist Cockpit

```bash
streamlit run ui/cockpit.py
```

---

## Project Structure

```
collections-ai/
├── data/
│   ├── raw/maple_data/          # Original dataset (31 tables)
│   ├── silver/                  # Cleaned per-domain tables
│   ├── golden/                  # golden_customer_360.parquet + features
│   └── features/                # Feature store (Parquet + lineage YAML)
├── pipeline/
│   ├── 01_ingest/               # Source loading + schema validation
│   ├── 02_quality/              # DQ checks + reports
│   ├── 03_identity/             # Entity resolution → Golden Financial ID
│   ├── 04_c360/                 # Customer 360 construction
│   ├── 05_collection_memory/    # Event model + chronological store
│   ├── 06_features/             # Feature engineering + feature store
│   ├── 07_financial_health/     # Financial Health Engine
│   └── 08_nba/                  # Policy-constrained Next Best Action
├── nlp/                         # NL-to-SQL + RAG pipeline
├── ui/                          # Streamlit Agent Assist Cockpit
├── models/                      # Model cards, trained artefacts
├── governance/                  # Access control, audit, lineage
├── tests/                       # Unit, integration, e2e tests
├── docs/
│   ├── architecture/            # Architecture diagrams (PNG/PDF)
│   ├── contracts/               # Data contracts (YAML)
│   └── reports/                 # DQ reports, model reports
├── config/                      # Pipeline configuration YAML
├── scripts/                     # Runner scripts
└── notebooks/                   # Exploratory analysis
```

---

## AI Tools Used

| Tool | Purpose | Where Deliberately NOT Used |
|---|---|---|
| Gemini API (gemini-2.0-flash) | NL→SQL translation, call transcript RAG, post-call summary | Affordability calculation (deterministic rules only) |
| Gemini Embeddings | Embedding agent notes + transcripts for semantic search | Identity resolution (deterministic/probabilistic only) |
| DuckDB | SQL over Parquet, NL→SQL execution | — |
| Splink | Probabilistic entity resolution | — |

---

## Governance Boundaries (Non-Negotiable)

1. Golden Financial ID is a system-internal governed key — not a government identifier  
2. AI must NOT invent customer facts  
3. Affordability calculated from governed data + deterministic rules — LLM is NOT the calculator of record  
4. Protected attributes (gender, marital status, citizenship, household, newcomer, accessibility, vulnerability, accent) are NEVER used in decisions  
5. Hardship/vulnerability flags trigger protection routing — not adverse treatment  
6. Low-confidence identity matches are NOT silently merged — they go to review queue  
7. Material customer-impact decisions require human review  
8. Every recommendation is explainable with evidence + policy reference  

---

## Documents

| Document | Purpose |
|---|---|
| `REQUIREMENTS.md` | Full requirements inventory |
| `REQUIREMENTS_TRACEABILITY.md` | Requirement → implementation → test → demo mapping |
| `DATA_SOURCES.md` | Source dataset documentation |
| `DATA_DICTIONARY_MAPPING.md` | Field-level mapping from source to golden C360 |
| `DATA_QUALITY_REPORT.md` | DQ issues found + handling decisions |
| `ARCHITECTURE.md` | Full architecture narrative |
| `IDENTITY_RESOLUTION.md` | Entity resolution methodology |
| `CUSTOMER_360.md` | C360 schema + lineage |
| `COLLECTION_MEMORY.md` | Event model documentation |
| `NLP_RETRIEVAL.md` | NLP layer design + guardrails |
| `FEATURE_STORE.md` | Feature definitions + lineage |
| `FINANCIAL_HEALTH.md` | Health engine formulas + reproducibility |
| `MODEL_CARD.md` | Model documentation |
| `NEXT_BEST_ACTION.md` | NBA policy rules + eligibility logic |
| `GOVERNANCE.md` | Governance framework |
| `LIMITATIONS_AND_TBC.md` | Known gaps + TBC fields |
| `DEMO_RUNBOOK.md` | Step-by-step demo instructions |
| `JUDGE_QA.md` | Prepared answers for live judging |
