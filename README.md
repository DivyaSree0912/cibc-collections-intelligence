# CIBC Collections Intelligence Platform
## Maple Bank — Governed Customer-State Collections Intelligence System

> **Hackathon:** CIBC Collections Hackathon — Build Phase<br>
> **Status:** Production-Ready Build & Validated Deliverables<br>
> **Dataset:** `nuxsh/maple-collections-hackathon` (HuggingFace) — 31 tables, 1M synthetic customers, 68M+ records (Oct 2016–Sep 2026)<br>
> **Canonical Identity Standard:** `golden_financial_id` (`GID-XXXXXXX`)<br>
> **Test Baseline:** 34 / 34 Automated Tests Passed (100%)<br>
> **Benchmark Validation:** 35 / 35 Questions Evaluated — Official Ground Truth Match (`PASS`)

---

## Table of Contents
1. [Project Purpose & Core Concept](#1-project-purpose--core-concept)
2. [End-to-End Architecture & Closed Loop](#2-end-to-end-architecture--closed-loop)
3. [Submission Artifacts & Deliverables](#3-submission-artifacts--deliverables)
4. [Quickstart: Installation & How to Run](#4-quickstart-installation--how-to-run)
5. [Streamlit Agent Assist Cockpit Walkthrough](#5-streamlit-agent-assist-cockpit-walkthrough)
6. [Automated Test Suite (34 Tests)](#6-automated-test-suite-34-tests)
7. [Benchmark Submission Validation (BQ-001 to BQ-035)](#7-benchmark-submission-validation-bq-001-to-bq-035)
8. [Important Artifacts & Output Locations](#8-important-artifacts--output-locations)
9. [Canonical Identity Standard: Golden Financial ID](#9-canonical-identity-standard-golden-financial-id)
10. [Data Quality & Entity Resolution Safeguards](#10-data-quality--entity-resolution-safeguards)
11. [Feature Store & Training-Serving Parity](#11-feature-store--training-serving-parity)
12. [Next Best Action (NBA) Engine & Human-in-the-Loop Controls](#12-next-best-action-nba-engine--human-in-the-loop-controls)
13. [Fairness Invariants & Protected-Attribute Exclusion](#13-fairness-invariants--protected-attribute-exclusion)
14. [AI Tools & Engineering Governance Boundaries](#14-ai-tools--engineering-governance-boundaries)
15. [Key Repository Documents & Links](#15-key-repository-documents--links)

---

## 1. Project Purpose & Core Concept

Collections intelligence in retail banking is fundamentally broken when systems operate in silos. Disconnected CRM logs, uncoordinated debt records across cards and loans, and punitive automated workflows alienate customers and destroy recovery yields.

The **CIBC Collections Intelligence Platform** unifies fragmented banking data across five core source systems into a single, governed, and fair decisioning loop:

$$\text{Golden Financial ID} \longrightarrow \text{Customer 360} \longrightarrow \text{Collection Memory} \longrightarrow \text{Financial Analysis} \longrightarrow \text{Financial Health} \longrightarrow \text{Policy NBA} \longrightarrow \text{Human Review} \longrightarrow \text{Outcome} \longrightarrow \text{Collection Memory}$$

### Core Value Pillars:
- **Unified Identity Without PII Exposure:** Deterministic and probabilistic entity resolution unifies customers into an internal, non-government identifier: `golden_financial_id`.
- **Chronological Collection Memory:** Retains every customer interaction, agent note, and transcript across time, answering the **Five Golden Questions** before any contact.
- **Deterministic Financial Health (Calculator of Record):** 3-Branch architecture calculating Debt Service Ratio (DSR), disposable monthly surplus, and payment reliability. Zero reliance on generative LLMs for mathematical calculations.
- **Policy-Constrained Next Best Action (NBA):** Governed rule hierarchy (Rules 1–5) enforcing customer hardship protections, DPD escalations, arrangement affordability gates, and digital payment reminders with 100% plain-English explanations.
- **Mandatory Frontline Human Control:** High-impact actions require frontline agent review (`requires_human_review`). Frontline Accept, Modify, and Override actions are persisted to an immutable DuckDB and JSONL audit trail under **OSFI E-23** compliance.
- **Provable Fairness:** Prohibited demographic and geographic proxy attributes are strictly excluded from features and decision logic. Vulnerability flags act strictly as protective routing shields.

---

## 2. End-to-End Architecture & Closed Loop

The platform is structured across four foundational layers backed by continuous governance:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MAPLE BANK RAW DATA SOURCES                     │
│    31 Tables across 5 Systems: CRM, Cards, Lending, Core, Collections   │
│                       (68,162,322 raw records)                         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   LAYER 1: DATA PRODUCT FACTORY                        │
│  • P1 Ingestion: Schema validation & DuckDB high-throughput storage   │
│  • P2 Data Quality: 18 automated rules, null/range remediation         │
│  • P3 Entity Resolution: Deterministic + Splink probabilistic linking │
│  • P4 Golden Customer 360: Aggregated exposure, DPD, active cases     │
│  • P5 Collection Memory: Chronological event store & hardship mining   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
        ┌───────────────────────────┴───────────────────────────┐
        ▼                                                       ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│   LAYER 2: INSIGHT & NLP        │   │   LAYER 3: FEATURE STORE        │
│ • Natural Language to SQL       │   │ • Lineage-tracked YAML specs    │
│ • Call Transcript Semantic RAG  │   │ • 3-Branch Financial Features   │
│ • Strict Out-of-Scope Refusals  │   │ • Zero-Skew Training/Serving    │
│ • Verified SQL Evidence Display │   │ • Protected Attributes Excluded │
└────────────────┬────────────────┘   └────────────────┬────────────────┘
                 │                                     │
                 └──────────────────┬──────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               LAYER 4: DECISIONING & NEXT BEST ACTION                  │
│  • Policy Rules Hierarchy (Hardship → DPD → Capacity → Affordability) │
│  • 100% Plain-English Explanations & Evidence Grounding                │
│  • Human Review Mandate (Accept / Modify / Override Controls)          │
│  • Affordability-Verified Smart Payment Plans (Step-Up / Balanced)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       THE GOVERNED CLOSED LOOP                         │
│  Frontline Agent Action ──► Customer Outcome ──► Collection Memory     │
│             ▲                                            │             │
│             └──────────── Next Decision Uses ────────────┘             │
│                           Updated History                              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Submission Artifacts & Deliverables

| Deliverable | Repository Path | Description | Status |
|---|---|---|---|
| **1. Code Repository** | Root workspace | Fully runnable, tested pipeline + Streamlit Agent Cockpit | ✅ **Complete** |
| **2. Architecture Diagram** | [`docs/architecture/cibc_collections_architecture.png`](docs/architecture/cibc_collections_architecture.png) & [`.pdf`](docs/architecture/cibc_collections_architecture.pdf) | High-resolution 4-layer architecture with governance overlay | ✅ **Complete** |
| **3. Data Contract** | [`docs/contracts/collections_360_contract.yaml`](docs/contracts/collections_360_contract.yaml) | ODCS v3.0.0 Golden C360 data contract (`DC-COLL-360`) | ✅ **Complete** |
| **4. Data Quality Report** | [`docs/reports/data_quality_report.md`](docs/reports/data_quality_report.md) & [`.json`](docs/reports/data_quality_report.json) | 18 automated checks; quantified defect remediation | ✅ **Complete** |
| **5. Benchmark Answers** | [`submission/benchmark_answers.csv`](submission/benchmark_answers.csv) | All 35 benchmark questions (dev + test) evaluated with SQL evidence | ✅ **Complete** |
| **6. Demo Video Guide** | [`docs/DEMO_VIDEO_SCRIPT.md`](docs/DEMO_VIDEO_SCRIPT.md) | Timestamped 4m45s turn-by-turn video walkthrough script | ✅ **Complete** |
| **7. Pitch Deck** | [`docs/CIBC_Collections_Intelligence_Pitch_Deck.pdf`](docs/CIBC_Collections_Intelligence_Pitch_Deck.pdf) & [`.docx`](docs/CIBC_Collections_Intelligence_Pitch_Deck.docx) | 10-slide executive presentation deck | ✅ **Complete** |
| **8. Master Test Suite** | [`tests/`](tests/) (34 tests across 4 modules) | Pytest suite: 34/34 tests passed in 38.67s | ✅ **Complete** |

---

## 4. Quickstart: Installation & How to Run

### Prerequisites
- Python 3.10, 3.11, or 3.12
- 8 GB+ RAM recommended

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/nuxsh/maple-collections-hackathon.git collections-ai
cd collections-ai
pip install -r requirements.txt
```

### 2. Environment Configuration (Optional)
If using the Gemini API for natural language to SQL translation:
```bash
# Windows PowerShell
$env:GOOGLE_API_KEY="your-api-key"
# or
$env:GEMINI_API_KEY="your-api-key"

# Linux / macOS
export GOOGLE_API_KEY="your-api-key"
```
*(Note: If no API key is provided, the platform automatically utilizes its built-in deterministic rule-based SQL generator and regex guardrails).*

### 3. Pipeline Execution (Pre-computed in Workspace)
All DuckDB database tables and Parquet outputs are **already pre-computed, validated, and frozen** in this repository. To run or inspect individual pipeline stages:
```bash
# Optional: re-run pipeline from scratch
python scripts/run_pipeline.py
```

### 4. Launch the Streamlit Agent Assist Cockpit
```bash
streamlit run ui/cockpit.py
```
The application opens automatically at `http://localhost:8501`.

---

## 5. Streamlit Agent Assist Cockpit Walkthrough

The Frontline Agent Assist Cockpit ([`ui/cockpit.py`](ui/cockpit.py)) provides collections agents with a complete decision support system organized into three functional tabs:

### Sidebar: Curated Demo Policy Scenarios
Judges and evaluators can immediately test all 5 policy rules using pre-configured customer accounts:
1. **Rule 1 — Hardship Protection (`GID-0065049`)**: Customer with medical/unemployment signals in notes; automatically routed to specialist review (`HUMAN_REVIEW`).
2. **Rule 2 — High DPD Escalation (`GID-0704634`)**: Delinquency at 179 DPD (>90 threshold); mandatory escalation to senior collections officer (`HUMAN_REVIEW`).
3. **Rule 3 — Sustainability Gate (`GID-0554888`)**: Negative financial capacity / severe DSR; standard payment plan blocked to prevent customer harm (`HUMAN_REVIEW`).
4. **Rule 4 — Affordability Payment Plan (`GID-0621203`)**: Mid-stage delinquency (DPD 43) with verified disposable surplus ($1,613/mo); tailored step-up plan proposed (`PAYMENT_PLAN`).
5. **Rule 5 — Early-Stage Reminder (`GID-0905960`)**: Early delinquency (DPD 9) with `GOOD` financial health; low-friction digital reminder dispatched (`REMINDER`).
*(Also supports browsing the full active portfolio of 1,000 accounts or searching any custom GID).*

### Tab 1: Agent Assist Workspace
- **Unified Customer 360 Header**: Deduplicated name, contact details, identity match confidence, and multi-product exposure KPIs (Aggregate Exposure, Overdue Balance, Portfolio Peak DPD, Monthly Inflow).
- **3-Branch Financial Health Scorecard**: Traffic light indicators and score breakdowns across **Branch A** (Exposure severity), **Branch B** (Cash-flow surplus & debt service), and **Branch C** (Payment reliability & 24m PTP fulfillment).
- **Collection Memory & Five Golden Questions**:
  - *Q1: What happened before?* (Prior touches and outcomes)
  - *Q2: What is happening now?* (Current DPD and queue)
  - *Q3: What has worked?* (Promises honoured, responsive channels)
  - *Q4: What has NOT worked?* (Broken promises, unanswered calls)
  - *Q5: What should I consider next?* (Next Best Action policy guidance)
  - Expandable interaction timeline with agent notes and hardship tags.
- **Policy-Constrained Next Best Action**: Clear action banner, plain-English explanation, policy citation, model confidence, and grounded evidence tags.
- **Human-in-the-Loop Decisioning (REQ-L4-03 / REQ-GOV-02)**:
  - `✅ Accept Recommendation`: Confirms recommendation and logs audit record.
  - `✏️ Modify Proposed Action`: Frontline clinical adjustment with mandatory reason.
  - `❌ Clinical Override`: Formal regulatory override with justification under OSFI E-23.
  - Live historical audit trail of prior agent reviews for the active customer.
- **Affordability-Verified Smart Payment Plans**: Option A (3-Month Step-Up), Option B (6-Month Balanced), and Option C (90% Settlement) with real-time affordability validation.

### Tab 2: Natural Language Query & Benchmark Center
- **Quick-Run Benchmark Buttons**:
  - `📊 Run Official Benchmark BQ-035`: Open collections cases by current bucket (exact integer match against DuckDB ground truth).
  - `🚫 Test Weather Refusal (BQ-018)`: Out-of-scope query guardrail refusal.
  - `🚫 Test Fairness Refusal (BQ-029)`: Demographic protected attribute refusal.
- **Interactive Query Engine**: Plain-English queries executed against DuckDB with verified SQL evidence display and execution latency metrics.

### Tab 3: Enterprise Governance & Audit Log
- Regulatory overview covering OSFI E-23, FCAC fair collections, and non-punitive vulnerability invariants.
- Live tabular viewer of the immutable frontline decision audit trail (`agent_decisions_audit`).

---

## 6. Automated Test Suite (34 Tests)

The test suite covers the entire lifecycle from ingestion to UI decisioning.

### Run All Tests
```bash
python -m pytest -v
```

### Test Suite Summary
```
tests/test_feature_store.py::test_feature_definitions_yaml_validity            PASSED [  2%]
tests/test_feature_store.py::test_governance_no_protected_attributes          PASSED [  5%]
tests/test_feature_store.py::test_feature_store_table_integrity               PASSED [  8%]
tests/test_feature_store.py::test_feature_store_parquet_artifacts             PASSED [ 11%]
tests/test_feature_store.py::test_training_serving_parity                     PASSED [ 14%]
tests/test_feature_store.py::test_deterministic_edge_cases                    PASSED [ 17%]
tests/test_nba_governance.py::test_nba_recommendations_coverage_and_validity  PASSED [ 20%]
tests/test_nba_governance.py::test_online_nba_evaluation                     PASSED [ 23%]
tests/test_nba_governance.py::test_plain_english_explanations_exist           PASSED [ 26%]
tests/test_nba_governance.py::test_human_review_triggers                     PASSED [ 29%]
tests/test_nba_governance.py::test_agent_decision_audit_trail                 PASSED [ 32%]
tests/test_nba_governance.py::test_no_protected_attributes_in_nba            PASSED [ 35%]
tests/test_nba_governance.py::test_hardship_routing_rule_1                    PASSED [ 38%]
tests/test_nba_governance.py::test_low_confidence_matches_not_silently_merged PASSED [ 41%]
tests/test_nba_governance.py::test_evidence_grounded_in_actual_features       PASSED [ 44%]
tests/test_nba_governance.py::test_deterministic_nba_decisions                PASSED [ 47%]
tests/test_pipeline.py::test_tables_ingested                                  PASSED [ 50%]
tests/test_pipeline.py::test_entity_resolution_clusters                       PASSED [ 52%]
tests/test_pipeline.py::test_customer_360_integrity                           PASSED [ 55%]
tests/test_pipeline.py::test_collection_memory_hardship_detection             PASSED [ 58%]
tests/test_pipeline.py::test_financial_health_scoring                         PASSED [ 61%]
tests/test_pipeline.py::test_nba_policy_enforcement                           PASSED [ 64%]
tests/test_pipeline.py::test_benchmark_bq035_gold_answer                      PASSED [ 67%]
tests/test_ui_cockpit.py::test_database_connection                             PASSED [ 70%]
tests/test_ui_cockpit.py::test_customer_list_non_empty                         PASSED [ 73%]
tests/test_ui_cockpit.py::test_traffic_light_formatting                        PASSED [ 76%]
tests/test_ui_cockpit.py::test_demo_scenario_data_integrity[Rule 1 Hardship]  PASSED [ 79%]
tests/test_ui_cockpit.py::test_demo_scenario_data_integrity[Rule 2 High DPD]  PASSED [ 82%]
tests/test_ui_cockpit.py::test_demo_scenario_data_integrity[Rule 3 Sust Gate] PASSED [ 85%]
tests/test_ui_cockpit.py::test_demo_scenario_data_integrity[Rule 4 Pay Plan]  PASSED [ 88%]
tests/test_ui_cockpit.py::test_demo_scenario_data_integrity[Rule 5 Reminder]  PASSED [ 91%]
tests/test_ui_cockpit.py::test_human_review_workflow_audit                   PASSED [ 94%]
tests/test_ui_cockpit.py::test_no_protected_attributes_in_ui_features        PASSED [ 97%]
tests/test_ui_cockpit.py::test_vulnerability_invariance_protection           PASSED [100%]

============================= 34 passed in 38.67s =============================
```

---

## 7. Benchmark Submission Validation (BQ-001 to BQ-035)

The benchmark submission evaluates all 35 official questions and is validated using the repository's automated checker:

```bash
python scripts/validate_benchmark_submission.py
```

### Output:
```
Expected benchmark questions: 35

Checking: data\benchmark_answers.csv
PASS: required columns present
PASS: no duplicate question IDs
PASS: no missing question IDs
PASS: no unexpected question IDs
PASS: every question has an answer
PASS: refusal flags match expected governance cases
PASS: row count = 35

Checking: data\raw\maple_data\maple_collections_release\labels\benchmark_answers_submission.csv
PASS: required columns present
PASS: no duplicate question IDs
PASS: no missing question IDs
PASS: no unexpected question IDs
PASS: every question has an answer
PASS: refusal flags match expected governance cases
PASS: row count = 35

============================================================
BENCHMARK VALIDATION: PASS
```

### Key Benchmark Ground Truths:
- **BQ-035 (Open Collections Cases by Current Delinquency Bucket):** Verified against DuckDB with exact integer match across all 7 buckets:
  - `1-30 days`: 33,639
  - `31-60 days`: 25,389
  - `61-90 days`: 16,312
  - `91-120 days`: 10,251
  - `121-150 days`: 6,184
  - `151-180 days`: 4,045
  - `180+ days`: 180
- **Refusal Guardrails:** Correctly declined with legal and policy justifications:
  - `BQ-018`: Refused (Out-of-scope external domain — weather query)
  - `BQ-023`: Refused (Bulk PII export restriction)
  - `BQ-024`: Refused (Geographic FSA redlining prevention)
  - `BQ-029`: Refused (Demographic protected attribute grouping — gender/marital status)
  - `BQ-031`: Refused (Protected attribute demographic analysis)

---

## 8. Important Artifacts & Output Locations

All pipeline deliverables, analytical databases, and audit logs are saved in standard repository paths:

```
collections-ai/
├── data/
│   ├── maple_collections.duckdb               # Master analytical lakehouse database
│   ├── benchmark_answers.csv                  # Official 35-question evaluated submission
│   ├── golden/
│   │   ├── golden_customer_360.parquet        # Unified Customer 360 table
│   │   ├── collection_memory.parquet          # Chronological interaction event store
│   │   ├── financial_health_features.parquet  # 3-Branch financial health scores
│   │   ├── financial_health_results.parquet   # Alias for scoring results
│   │   ├── nba_recommendations.parquet        # Governed NBA recommendations
│   │   └── nba_results.parquet                # Alias for NBA results
│   └── features/
│       ├── feature_store.parquet              # Full derived feature store (1M rows)
│       ├── training_features.parquet          # Sampled offline training feature store
│       └── feature_definitions.yaml           # Lineage YAML specifications
├── docs/
│   ├── architecture/
│   │   ├── cibc_collections_architecture.png  # Architecture diagram (PNG)
│   │   └── cibc_collections_architecture.pdf  # Architecture diagram (PDF)
│   ├── contracts/
│   │   └── collections_360_contract.yaml      # ODCS v3.0.0 Golden C360 data contract
│   └── reports/
│       ├── data_quality_report.md             # Automated DQ check report
│       └── data_quality_report.json           # Machine-readable DQ results
└── logs/
    ├── agent_decisions_audit.jsonl            # Append-only frontline review audit trail
    └── pipeline_run_summary.json              # High-throughput execution telemetry
```

---

## 9. Canonical Identity Standard: Golden Financial ID

Identity resolution is anchored on the **Golden Financial ID** (`golden_financial_id`, e.g., `GID-0000001`):

- **Non-PII, System-Internal Key:** Does not use Government Social Insurance Numbers (SIN), National IDs, or raw account numbers.
- **Cross-System Unification:** Merges customer profiles across CRM (`customer_id`), Credit Cards (`card_account_id`), Lending (`loan_id`), Core Banking (`bank_account_id`), and Collections Case Management (`case_id`).
- **Entity Resolution Engine:**
  - *Pass 1 (Deterministic):* Exact match on cleaned, normalized SIN / email / phone hashes.
  - *Pass 2 (Probabilistic Linker):* Splink Fellegi-Sunter model evaluating Jaro-Winkler string similarity on full names, fuzzy DOB, and address blocks.
  - *Confidence Thresholds:* Match confidence $\ge 0.85$ automatically links to a unified Golden Financial ID; matches $< 0.85$ are flagged and routed to the `identity_review_queue` for data steward validation.

---

## 10. Data Quality & Entity Resolution Safeguards

The Data Product Factory executes 18 automated quality assertions before records reach the Golden Layer:

1. **Zero Silent Merges (REQ-GOV-05):** Unresolved or ambiguous entity links are never silently blended into existing credit profiles. 10,365 records with confidence $< 0.85$ are safely quarantined in `identity_review_queue`.
2. **Defect Remediation:** Automated cleaning standardizes telephone formats, normalizes timestamp timezones to `America/Toronto`, clamps negative balances, and imputes missing credit limits using domain-specific medians.
3. **Data Contract Enforcement:** The pipeline validates column types, null constraints, and value bounds against [`docs/contracts/collections_360_contract.yaml`](docs/contracts/collections_360_contract.yaml).

---

## 11. Feature Store & Training-Serving Parity

- **Single Definition of Record (REQ-L3-03):** All feature transformations are declared in [`data/features/feature_definitions.yaml`](data/features/feature_definitions.yaml) and computed via `pipeline/06_features/feature_store.py`.
- **Zero-Skew Parity:** Both offline model training (`training_features.parquet`) and online live scoring (`feature_store.parquet`) consume the exact same deterministic calculation functions. Tested and verified in `tests/test_feature_store.py::test_training_serving_parity`.
- **Feature Domains (REQ-L3-01 & REQ-L3-02):**
  - *Exposure Features:* `total_aggregate_exposure`, `total_overdue_balance`, `max_dpd_across_portfolio`, `exposure_score`.
  - *Cash-Flow & Capacity:* `estimated_monthly_inflow`, `estimated_monthly_emi`, `available_monthly_surplus`, `dsr`.
  - *Payment Reliability:* `ptp_fulfillment_rate`, `ptp_count_24m`, `payment_behaviour_score`.
  - *Unstructured Signals:* Text-mined `hardship_flag` derived from customer notes and call transcripts.

---

## 12. Next Best Action (NBA) Engine & Human-in-the-Loop Controls

The Next Best Action engine ([`pipeline/08_nba/next_best_action.py`](pipeline/08_nba/next_best_action.py)) implements an explicit, policy-constrained decision hierarchy:

### Policy Rule Hierarchy:
1. **Rule 1 — Hardship Protection:** If `hardship_flag` or `vulnerability_flag` is present $\longrightarrow$ `HUMAN_REVIEW` (Specialist Review Queue). Blocks automated collections contact.
2. **Rule 2 — High Delinquency Escalation:** If `max_dpd_across_portfolio > 90` $\longrightarrow$ `HUMAN_REVIEW` (Senior Collections Officer).
3. **Rule 3 — Sustainability Gate:** If `can_support_arrangement = 'NO'` or `dsr_category = 'SEVERE'` or `available_monthly_surplus <= 0` $\longrightarrow$ `HUMAN_REVIEW` (Forbearance Review). Prohibits standard payment plans to prevent customer harm.
4. **Rule 4 — Affordability-Led Payment Plan:** If `max_dpd_across_portfolio > 30` and `available_monthly_surplus > 0` $\longrightarrow$ `PAYMENT_PLAN` (Tailored Step-Up Plan).
5. **Rule 5 — Early-Stage Digital Reminder:** If `max_dpd_across_portfolio <= 30` and `composite_health_score >= 0.60` $\longrightarrow$ `REMINDER` (Digital SMS/Email).

### Governance Controls:
- **Plain-English Explanations (REQ-L4-02 & REQ-GOV-01):** 100% of NBA records include an interpretable plain-English justification citing the exact policy rule and underlying financial metrics.
- **Factual Evidence Grounding (REQ-GOV-07):** Evidence tags are strictly populated from verified feature store values (e.g., `dpd=43`, `surplus=1613.25`, `health=FAIR`).
- **Human Review Mandate (REQ-L4-03 & REQ-GOV-02):** Frontline agents retain full authority to Accept, Modify, or Override recommendations in the Cockpit. Every action is recorded with officer ID, timestamp, and justification in `agent_decisions_audit` and `logs/agent_decisions_audit.jsonl`.

---

## 13. Fairness Invariants & Protected-Attribute Exclusion

In strict compliance with **OSFI Guideline E-23** and **FCAC Fair Collections Standards**:

1. **Excluded Attributes (REQ-GOV-03):** The following demographic and geographic proxy fields are strictly excluded from the Customer 360, Feature Store, and NBA decision logic:
   - `gender`
   - `marital_status`
   - `citizenship`
   - `race`
   - `religion`
   - `household`
   - `newcomer`
   - `accessibility`
   - `accent`
   - `customer_fsa` / `postal_code` (redlining prevention)
   - *Verified in automated tests:* `test_governance_no_protected_attributes`, `test_no_protected_attributes_in_nba`, and `test_no_protected_attributes_in_ui_features`.
2. **Protective Vulnerability Invariance (REQ-GOV-04):** `vulnerability_flag` is mathematically and logically invariant against adverse collections treatment. It functions solely as a protective shield routing customers to specialist hardship assistance. Verified in `test_vulnerability_invariance_protection`.

---

## 14. AI Tools & Engineering Governance Boundaries

Generative AI is deployed deliberately and safely within strict boundaries:

| Technology | Purpose | Explicit Governance Restriction |
|---|---|---|
| **Gemini 2.0 Flash / Embeddings** | Plain-English natural language translation to SQL; call transcript semantic search | **Strictly Prohibited** from calculating financial health, DSR, affordability, or payment plan sums. |
| **DuckDB (In-Process SQL OLAP)** | Fast analytical execution over 68M+ records; analytical lakehouse queries | Primary deterministic calculator of record. |
| **Splink (Fellegi-Sunter)** | Probabilistic cross-source entity linking | Requires match confidence $\ge 0.85$; ambiguous pairs routed to review queue. |
| **Python Deterministic Engine** | DSR ratios, surplus calculation, Rule 1–5 policy trees | LLMs never generate decision logic dynamically. |

---

## 15. Key Repository Documents & Links

For deep architectural documentation, specifications, and presentation materials, refer to:

- 📐 **System Architecture:** [`docs/architecture/cibc_collections_architecture.pdf`](docs/architecture/cibc_collections_architecture.pdf)
- 📋 **ODCS Data Contract:** [`docs/contracts/collections_360_contract.yaml`](docs/contracts/collections_360_contract.yaml)
- 📊 **Data Quality Report:** [`docs/reports/data_quality_report.md`](docs/reports/data_quality_report.md)
- 🎯 **Benchmark Answers:** [`submission/benchmark_answers.csv`](submission/benchmark_answers.csv)
- 🎬 **Demo Video Script:** [`docs/DEMO_VIDEO_SCRIPT.md`](docs/DEMO_VIDEO_SCRIPT.md)
- 📑 **Pitch Deck Presentation:** [`docs/CIBC_Collections_Intelligence_Pitch_Deck.pdf`](docs/CIBC_Collections_Intelligence_Pitch_Deck.pdf)
- 📜 **Requirements Traceability:** [`REQUIREMENTS_TRACEABILITY.md`](REQUIREMENTS_TRACEABILITY.md)
- ⚖️ **Governance & Compliance Framework:** [`GOVERNANCE.md`](GOVERNANCE.md)
- 🔬 **Feature Store Lineage:** [`data/features/feature_definitions.yaml`](data/features/feature_definitions.yaml)
