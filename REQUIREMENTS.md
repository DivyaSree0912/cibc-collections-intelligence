# REQUIREMENTS.md
# CIBC Collections Intelligence — Complete Requirements Inventory

## Source Documents

| Document | Key Information |
|---|---|
| `CIBC Collections Hackathon Problem Statement.pdf` | 3 layers, judging criteria, submission format, governance rules |
| `CIBC Hackathon Build Phase - Instructions.pdf` | Dataset location, exact submission requirements, timeline, what each layer must show |
| `maple_collections_release/README.md` | Dataset schema, 31 tables, 5 source systems, field conventions |
| `maple_collections_release/files/docs/data_contracts/DC-COLL-001` | Example data contract format |
| Previous architecture documents | Golden Financial ID concept, 3-branch financial health, Collection Memory, Fair Collections |

---

## Judging Criteria (Build Phase)

| Criterion | Weight | Key Evidence Needed |
|---|---|---|
| Technical quality and working demo | 30% | End-to-end pipeline running; benchmark CSV with correct answers + SQL shown |
| Business understanding | 20% | Problem framing, agent value proposition, metric impact |
| Presentation and storytelling | 20% | Pitch deck (≤10 slides), demo video (≤5 min) |
| Innovative ideas | 15% | Golden Financial ID, Collection Memory, Fair Collections, closed-loop |
| Team work | 15% | Visible collaboration, clear contribution split |

---

## Mandatory Submission Artifacts

| # | Artifact | Format | Owner |
|---|---|---|---|
| 1 | Code repository (GitHub, private + organiser access) | Git repo | Both |
| 2 | Architecture diagram (final) | PDF or PNG in repo | Member 1 |
| 3 | Data contract for golden C360 | YAML or JSON | Member 1 |
| 4 | Data quality report | Markdown or PDF | Member 1 |
| 5 | Benchmark answers CSV | `question_id, answer, sql_or_sources, refused` | Member 2 |
| 6 | Demo video (≤5 min, YouTube unlisted or Drive) | Video link | Member 2 |
| 7 | Pitch deck (≤10 slides) | PDF | Member 2 |
| 8 | README covering: how to run, what changed from design, AI tools used | Markdown | Both |

---

## Layer Requirements

### Layer 1 — Data Product Factory

**Must show:**
- REQ-L1-01: Raw-to-curated-to-golden C360 pipeline (code, runnable)
- REQ-L1-02: Customer ID matching across the **five source systems** with a match confidence score
- REQ-L1-03: Data quality checks (with report)
- REQ-L1-04: Data contract for golden C360 (YAML/JSON, using DC-COLL-001 as starting point)

### Layer 2 — Insight and NLP

**Must show:**
- REQ-L2-01: Plain-English questions answered over the C360
- REQ-L2-02: The SQL or source shown with every answer
- REQ-L2-03: Out-of-scope questions refused (with reason)

### Layer 3 — Feature Store

**Must show:**
- REQ-L3-01: Features from structured data
- REQ-L3-02: Features from text or voice
- REQ-L3-03: One feature definition used for both training and live scoring

### Layer 4 — Models and Decisioning (chosen use case: **Next Best Action**)

**Must show:**
- REQ-L4-01: A working model or agent for Next Best Action
- REQ-L4-02: Plain-English explanation of each decision
- REQ-L4-03: A point where a human reviews or overrides

---

## Governance Requirements (Non-Negotiable)

- REQ-GOV-01: Every decision shown to a collections agent comes with a plain-English reason
- REQ-GOV-02: A human can review anything that affects a customer
- REQ-GOV-03: No protected attributes in decisions (gender, marital status, citizenship, household, newcomer, accessibility, vulnerability, accent)
- REQ-GOV-04: Flag financial hardship
- REQ-GOV-05: Low-confidence identity matches must NOT be silently merged
- REQ-GOV-06: Affordability must be calculated from governed data and deterministic rules (LLM is NOT the calculator of record)
- REQ-GOV-07: AI must not invent customer facts

---

## Dataset Facts (from Build Phase PDF)

- Source: `huggingface.co/datasets/nuxsh/maple-collections-hackathon`
- Size: 2.3 GB (without voice); 4.7 GB (with voice WAV files)
- Synthetic: 1,000,000 customers; October 2016 – September 2026; snapshot date 28 Sep 2026
- **5 source systems** (specific system names: TBC — to be confirmed from dataset README)
- 31 tables (CSV and Parquet)
- Call transcripts (JSON)
- Policy documents included
- Data dictionary included
- 500 public labels each for notes and transcripts
- **Data quality issues are deliberate:** duplicates, missing values, mixed date formats, mismatched IDs, schema drift
- Protected attributes included only to test fairness: gender, marital status, citizenship, household, newcomer, accessibility, vulnerability, accent
- Benchmark questions: answers CSV template in release README

---

## Timeline

| When | Event |
|---|---|
| 3 Oct, 9:00 AM | Build phase starts, dataset released |
| 3–4 Oct | Industry reps review top 10 designs + insight session |
| 4 Oct, 7:00 PM | Extra benchmark questions released |
| 4 Oct, 9:00 PM | Submission deadline |
| After judging | 10 finalists get days to refine |
| TBA | Final presentations at partner office |

---

## Technical Constraints

- Use DuckDB or Polars for large tables (not pandas — too slow)
- ~10 GB free disk space needed (16 GB with voice files)
- Paid LLM APIs allowed; data is synthetic so can be sent to any API
- Commits after 9:00 PM on 4 Oct are not considered
- Benchmark answers scored automatically — do NOT edit by hand
