# JUDGE_QA.md
# CIBC Collections Intelligence — Prepared Answers for Live Judging

> These answers are evidence-backed, concise, and aligned to the actual implementation.
> Each answer references where in the code the claim is demonstrated.

---

## Business Questions

**Q: What problem are you solving?**

Collections agents today face three unsolvable problems: (1) A customer's financial history is fragmented across 5 different source systems with no unified view. (2) Every agent starts from zero — no memory of what was said, promised, or failed before. (3) Collection actions ignore whether a customer *can* pay, focusing only on whether they *owe* money.

We solve all three with one architecture: Golden Financial ID unifies the identity, Collection Memory persists the history, and the Financial Health Engine determines whether a proposed arrangement is sustainable.

**Q: Who uses the system?**

Authorised collections agents at Maple Bank. They access it through the Agent Assist Cockpit (Streamlit UI). A collections supervisor can use the NL Query panel to ask portfolio-level questions. No customer-facing interface exists — this is an internal agent tool.

**Q: What changes for the collections agent?**

Before: The agent opens a case with an overdue amount and a customer name. That's it.

After: The agent opens the Cockpit and instantly sees the customer's full financial context, what happened in every prior contact, what the Financial Health Engine says about their capacity to pay, a policy-constrained recommended action with an explanation, and — if relevant — three affordability-verified payment plan options. All in one screen.

---

## Architecture Questions

**Q: Why Golden Financial ID?**

The dataset has 5 source systems, each with its own customer key. Entity resolution joins these into one governed `golden_financial_id` (GID-XXXXXXX). It is system-internal — not a government identifier, not a universal standard. It's the stable key that allows Customer 360, Collection Memory, Financial Health, and NBA to all refer to the same person.

Code: `pipeline/03_identity/entity_resolution.py`

**Q: How does identity resolution work?**

Pass 1 — Deterministic: Exact match on normalised phone, normalised email, or tax_id. Confidence = 1.0. Auto-linked.

Pass 2 — Probabilistic: Jaro-Winkler similarity on name/address. Score ≥ 0.92 = auto-linked. Score 0.85–0.91 = linked with REVIEW flag. Score < 0.85 = NOT merged — goes to `identity_review_queue`.

The review queue is surfaced in the Cockpit's Governance panel. Low-confidence matches are NEVER silently merged.

**Q: How does Customer 360 work?**

After GIDs are assigned, `build_c360.py` aggregates all source records per GID into `golden_customer_360`. Every field retains: source_table, lineage_last_updated, pipeline_version. Protected attributes (gender, marital status, citizenship, household, newcomer, accessibility, vulnerability, accent) are NEVER included in the C360.

**Q: How does Collection Memory work?**

It's a timestamped event log in DuckDB: `collection_memory`. Events come from contact_history, agent_notes, and call_transcripts. Every event is linked to a GID and an account. A `detect_hardship()` function scans note and transcript text for keywords (medical, job loss, bereavement, etc.) and sets a `hardship_flag`. This flag triggers PROTECTIVE routing — never adverse treatment.

The Five Golden Questions are generated from this table: What happened? What's now? What worked? What didn't? What next?

**Q: How does the NLP layer retrieve evidence?**

The agent types a plain-English question → `check_refusal()` first (blocks protected attribute queries) → Gemini API converts question to SQL → DuckDB executes SQL against the golden C360 → result + SQL returned to UI. The SQL is ALWAYS shown. There is no response without its evidence.

**Q: How does Financial Health work?**

Three deterministic branches:
- Branch A (Exposure Score): `total_aggregate_exposure / (estimated_monthly_inflow × 12)`, normalised 0–1
- Branch B (Cash-Flow Stress): salary credit lag days → LOW/MODERATE/HIGH/SEVERE
- Branch C (Payment Behaviour): `(ptp_fulfillment_rate × 0.5) + (1 - dpd_normalised) × 0.5`

Composite = weighted average (35% / 35% / 30%). DSR = `monthly_EMI / monthly_inflow`.

All formulas are in `financial_health.py` lines 60–130. The LLM is NEVER the calculator.

**Q: How does NBA work?**

Five explicit policy rules (documented in `next_best_action.py`):
1. Hardship/vulnerability → always HUMAN_REVIEW (protective)
2. DPD > 90 → HUMAN_REVIEW
3. Can't support arrangement → HUMAN_REVIEW + possibly PAYMENT_PLAN
4. Marginal financial position → PAYMENT_PLAN (agent must approve)
5. DPD ≤ 30 + GOOD/FAIR health → REMINDER eligible

Every output includes: recommended action, eligible actions, ineligible actions + reasons, explanation, evidence list, policy reference. Human agents see Accept / Modify / Override.

---

## Data Questions

**Q: Where did the data come from?**

`huggingface.co/datasets/nuxsh/maple-collections-hackathon` — 1,000,000 synthetic Maple Bank customers, 31 tables, Oct 2016 – Sep 2026. All data is synthetic. CC-BY-4.0 licence.

**Q: What fields are missing / TBC?**

Fields marked TBC in `golden_customer_360`: exact income/salary fields, property/asset fields, some contact channel fields. These are TBC until the data dictionary (DATA_DICTIONARY.xlsx in the dataset) is fully inspected. Any TBC field causes the Financial Health engine to lower the `data_completeness_pct` score and set `requires_human_review = True`.

**Q: How was data cleaned?**

Phones normalised (10-digit, country code stripped). Dates validated to ISO-8601, mixed formats flagged in DQ report. Duplicates detected per primary key. Range checks on DPD (must be ≥ 0), balances (must be ≥ 0). Full DQ report at `docs/reports/data_quality_report.md` with PASS/WARN/FAIL per rule.

---

## AI/ML Questions

**Q: Where is AI used?**

1. NL-to-SQL conversion (Gemini API) — converts agent's plain-English questions to SQL
2. Collection Memory RAG (Gemini Embeddings + ChromaDB) — retrieves relevant transcript/note chunks for the Five Golden Questions view
3. Post-call summary (Gemini API) — extracts structured information from call transcripts

**Q: Where is AI deliberately NOT used?**

Affordability calculation — 100% deterministic formula. Identity resolution — deterministic + Jaro-Winkler similarity (no LLM). NBA policy rules — explicit if/then logic. Data quality checks — rule-based.

**Q: How do you prevent hallucination?**

The NL-to-SQL approach means every answer is grounded in actual SQL execution. The result comes from the database, not from the LLM's memory. The LLM generates SQL; DuckDB runs it; the result is displayed alongside the SQL. The agent can inspect the SQL to verify it makes sense. The LLM is not asked to recall facts — it is asked to generate queries.

**Q: How do you explain recommendations?**

Every NBA record contains: `explanation` (plain English), `evidence` (list of data points that drove the decision), `policy_reference` (which policy rule applied), `eligible_actions`, `ineligible_actions` (with reasons). The UI displays all of this in the agent's Cockpit.

---

## Governance Questions

**Q: What prevents unfair treatment?**

1. Protected attributes (gender, marital status, citizenship, household, newcomer, accessibility, vulnerability, accent) are NEVER included in any model input, feature, or NBA rule.
2. Hardship flags trigger PROTECTION (human review), not adverse treatment.
3. Affordability is calculated from financial data — not demographic assumptions.
4. Every NBA decision is explainable with evidence.
5. Human agents retain control over material decisions.

**Q: What happens when the model is uncertain?**

If `data_completeness_pct` is below threshold, `requires_human_review = True` is set. NBA defaults to HUMAN_REVIEW when confidence is LOW. Unclear identity matches go to the review queue.

**Q: Can you audit the recommendation?**

Yes. `nba_recommendations` table contains: recommended action, eligible actions, ineligible actions + reasons, explanation, evidence, policy reference, policy version, computed_at timestamp. This is the audit record. Every run also writes to `audit_ingestion` table.

**Q: What happens after the customer outcome?**

The outcome is written as a new event to `collection_memory`. The next pipeline run reads the updated memory. The next NBA recommendation sees the updated state. This is the closed loop.

---

## Demo Questions

**Q: What happens if data is missing?**

TBC fields in C360 → `data_completeness_pct` decreases → `requires_human_review = True` → agent is shown a warning → case goes to human review. The system NEVER makes a recommendation based on assumed data.

**Q: What happens if two customers look similar?**

Probabilistic matching assigns a confidence score. If confidence is 0.85–0.91, both records are linked with a REVIEW flag visible in the Cockpit. If confidence is below 0.85, records are NOT merged — they remain separate in the `identity_review_queue`.

**Q: What happens if hardship is detected?**

NBA Rule 1 fires immediately: recommended_action = HUMAN_REVIEW. The explanation says: "Hardship or vulnerability signal detected. Policy requires specialist review before any collection action." The agent sees a red warning panel in the Cockpit. No automated collection action is taken.
