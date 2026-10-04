# LIMITATIONS_AND_TBC.md
# Known Limitations, Assumptions, and TBC Items

## TBC — Requires Dataset README Inspection

| Item | Status | Resolution Path |
|---|---|---|
| Exact 5 source system names | TBC | Read maple_collections_release/README.md |
| Exact customer key used by each source system | TBC | Read dataset README (it covers this explicitly) |
| Exact table names and schemas (all 31 tables) | TBC | Inspect downloaded Parquet/CSV files |
| Benchmark question format and columns | TBC | Read release README "Benchmark questions" section |
| Example data contract DC-COLL-001 | TBC | Read files/docs/data_contracts/ |
| Which fields are available for affordability calculation | TBC | Inspect data dictionary in release |
| Voice files (.wav) | NOT INCLUDED | Downloading without voice to save disk space; voice features = TBC |
| Income/salary fields | TBC | Must be confirmed from data dictionary — do not invent |
| Property/asset fields | TBC | Confirm from data dictionary; Future Concept only if not present |

---

## Confirmed Constraints (from Build Phase PDF)

| Item | Status | Source |
|---|---|---|
| Protected attributes NOT in decisions | CONFIRMED | Build Phase PDF p.4 |
| Human review for agent-impacting decisions | CONFIRMED | Build Phase PDF p.4 |
| Hardship flags required | CONFIRMED | Build Phase PDF p.4 |
| SQL shown with every NLP answer | CONFIRMED | Build Phase PDF p.2 |
| Out-of-scope questions refused | CONFIRMED | Build Phase PDF p.2 |
| Match confidence required for identity resolution | CONFIRMED | Build Phase PDF p.2 |
| Data quality issues are deliberate | CONFIRMED | Build Phase PDF p.2 |
| Benchmark CSV auto-scored | CONFIRMED | Build Phase PDF p.3 |

---

## Architectural Assumptions (Implementation Decisions)

| Assumption | Rationale | Risk |
|---|---|---|
| Using DuckDB as primary SQL engine | Build Phase PDF explicitly recommends DuckDB/Polars for large tables | Low |
| Using Gemini API for NL-to-SQL and RAG | Paid APIs allowed; data is synthetic | Low — cost risk if many calls |
| Using Splink for probabilistic entity resolution | Best Python library for this; well-documented | Medium — may need tuning |
| Streamlit for Agent Assist UI | Fastest working demo; no auth overhead needed for hackathon | Low |
| Skipping voice files | Save disk/time; text transcripts sufficient for demo | Low — note in README |
| Feature store as Parquet + YAML lineage files | Simple, portable, no server needed | Low |

---

## Fields That Cannot Be Fabricated

The following must be marked TBC until confirmed from the data dictionary:

- Income/salary amount
- Employment type
- Property value
- Asset details
- Any field not confirmed in the 31-table dataset

If a field cannot be confirmed, the corresponding feature/signal is marked TBC and not included in the model.
