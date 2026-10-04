# CIBC Collections Intelligence Platform — 5-Minute Demo Video Recording Script

> **Target Duration:** 4 minutes 45 seconds (Limit: ≤ 5 minutes)  
> **Presenter:** Frontline AI Engineer & Collections Solutions Architect  
> **Format:** Screen Recording with Voiceover (Streamlit Cockpit + DuckDB Terminal + Architecture)

---

## Video Outline & Timestamp Breakdown

| Timestamp | Duration | Section | On-Screen Visual | Audio Narration Focus |
|---|---|---|---|---|
| **0:00 – 0:45** | 45s | **1. Problem & Core Innovation** | Slide 1 & Architecture Diagram | Fragmented 5 source systems -> Golden Financial ID & Collection Memory |
| **0:45 – 1:30** | 45s | **2. Layer 1: Identity & C360** | DuckDB Terminal + Cockpit Panel 1 | Clustered 1.02M CRM records into 1M GIDs; zero silent merges; review queue |
| **1:30 – 2:30** | 60s | **3. Layer 2: NL-to-SQL & Benchmarks** | Cockpit NL Query Panel + SQL Output | Natural language exploration; executed SQL displayed; refusal guardrails |
| **2:30 – 3:30** | 60s | **4. Layer 3: Memory & Financial Health** | Cockpit Panels 2 & 3 | 3.5M events; Five Golden Questions; 3-branch Health traffic lights; DSR math |
| **3:30 – 4:15** | 45s | **5. Layer 4: Policy NBA & Smart Plans** | Cockpit Panels 4, 5 & 6 | 5 policy rules; plain-English explanation; Accept/Modify/Override; 3 plans |
| **4:15 – 4:45** | 30s | **6. Governance, Safety & Wrap-up** | Governance Box + Closing Slide | Zero protected attributes; hardship protection; business impact & vision |

---

## Detailed Speaker Script (Turn-by-Turn)

### [0:00 – 0:45] 1. The Core Problem & Dual Innovations

**[VISUAL: Display `docs/architecture/cibc_collections_architecture.png` on screen]**

> **Speaker:**  
> "Hello judges! Today we present the **CIBC Collections Intelligence Platform**, built for the Maple Bank collections hackathon.
>
> In retail banking, collections faces a fundamental flaw: customer data is fragmented across five disconnected source systems—CRM, Cards, Lending, Core Banking, and Collections. Every time a customer defaults, frontline agents start from zero, asking repetitive questions without understanding the customer's true financial story.
>
> We solve this with two core architectural pillars:
> 1. The **Golden Financial Identity Layer**, which unifies disparate customer accounts into one governed persistent identity (`GID-XXXXXXX`).
> 2. **Collection Memory**, a longitudinal event log that ensures no agent ever starts from scratch again.
>
> Let's see how this works in production across 68 million records."

---

### [0:45 – 1:30] 2. Layer 1: Data Product Factory & Entity Resolution

**[VISUAL: Switch to terminal showing `python scripts/run_pipeline.py` or DuckDB table counts, then open Streamlit Cockpit top panel]**

> **Speaker:**  
> "Our Layer 1 Data Product Factory ingests all 31 tables in DuckDB in just 32 seconds.
>
> Here in Phase 3, our Entity Resolution Engine performs deterministic clustering on normalized phone, email, and dates of birth. It unified 1,020,000 CRM profiles into 1,001,879 unique individuals, connecting 1.7 million cross-system records in under 15 seconds.
>
> Crucially, we enforce a strict safety rule: **zero silent merges**. Matches below 0.85 confidence are placed in our `identity_review_queue` for human data stewards.
>
> The result is our governed **Customer 360**, exported to Parquet under an ODCS v3.0.0 data contract, with protected demographic attributes strictly isolated."

---

### [1:30 – 2:30] 3. Layer 2: Insight Platform & Benchmark Validation

**[VISUAL: In Streamlit Cockpit, scroll to the 'NL Query Panel']**

> **Speaker:**  
> "Layer 2 provides our Grounded Natural Language Query Platform. When an agent or portfolio supervisor types a business question in plain English, our engine converts it into verified DuckDB SQL, executes it against the live lakehouse, and displays both the result and the exact SQL query.
>
> For instance, asking for 'Open collections cases by bucket' instantly executes:
> `SELECT current_bucket, count(*) FROM collections_cases WHERE outcome IS NULL GROUP BY 1`
> matching the official benchmark BQ-035 to the exact integer across all 7 delinquency buckets!
>
> Furthermore, we have built-in **Refusal Guardrails**:
> - If an agent asks for out-of-scope data like tomorrow's weather (BQ-018), it refuses.
> - If an agent attempts bulk PII exfiltration (BQ-023), it refuses.
> - If an agent queries protected grounds like citizenship or gender (BQ-029/031), it strictly declines to answer, enforcing regulatory fairness."

---

### [2:30 – 3:30] 4. Layer 3: Collection Memory & Financial Health Engine

**[VISUAL: Select an active customer profile (e.g., GID with hardship) in the Cockpit; showcase Panels 2 & 3]**

> **Speaker:**  
> "Layer 3 brings customer context alive.
>
> Here is **Collection Memory**, housing 3.58 million historical interaction events. It answers the **Five Golden Questions** on a single pane:
> *What happened before? What is happening now? What worked? What didn't work? And what should we consider next?*
>
> Our NLP engine scanned over 760,000 agent notes and uncovered 84,289 hidden hardship cases—identifying the 60% of hardship cases that manual flags miss.
>
> Next, look at our **3-Branch Financial Health Engine**:
> 1. **Branch A — Exposure Analysis:** evaluates cross-product debt against annual income.
> 2. **Branch B — Cash-Flow Stress:** tracks verifiable salary credits, payroll delays, and overdraft utilization.
> 3. **Branch C — Payment Behaviour:** evaluates promise-to-pay integrity over 24 months.
>
> The engine deterministically computes the true Debt Service Ratio (DSR) and surplus in DuckDB in under 1 second across 1 million customers. The LLM is **never** the calculator of record."

---

### [3:30 – 4:15] 5. Layer 4: Policy Next Best Action & Smart Payment Plans

**[VISUAL: Showcase Cockpit Panels 4, 5, and 6 (Recommendation card, Human review buttons, 3 Payment Plan cards)]**

> **Speaker:**  
> "Layer 4 drives policy-constrained decisioning.
>
> Our Next Best Action engine evaluates 93,240 active delinquent accounts against 5 non-negotiable policy rules:
> - If hardship or vulnerability is detected, Rule 1 triggers **Specialist Review** as a protective safeguard—never to penalize.
> - If DPD exceeds 90, Rule 2 escalates to senior review.
> - For early-stage delinquency with good financial health, Rule 5 triggers an automated digital reminder.
>
> Every single recommendation includes a **plain-English explanation**, cited policy reference, and factual evidence tags.
>
> Most importantly, we maintain **full human control**. Frontline agents see clear **Accept**, **Modify**, and **Override** controls.
>
> When a payment arrangement is appropriate, the system generates three tailored Smart Payment Plans—Fast-Track, Balanced, and Step-Up—each verified against the customer's actual monthly surplus."

---

### [4:15 – 4:45] 6. Governance, Safety & Value Impact

**[VISUAL: Show Governance Panel with audit timestamps, then show Slide 10 summary]**

> **Speaker:**  
> "Finally, enterprise governance is woven into every layer:
> - Zero protected demographic attributes are used in any model.
> - Every score, action, and agent override is logged to an immutable audit trail.
> - The entire pipeline runs end-to-end on 68 million records in under 70 seconds.
>
> By transforming collections from aggressive dunning to empathetic, data-backed rehabilitation, we achieve a projected **+28% increase in promise fulfillment**, a **-40% reduction in call handling time**, and protect the bank's long-term customer relationships.
>
> Thank you!"

---

## Live Demo Cheat-Sheet for Presenter

1. **Start Streamlit:** `streamlit run ui/cockpit.py`
2. **Browser URL:** `http://localhost:8501`
3. **Key Customer to Search:** Select from the dropdown (contains active delinquent accounts with complete Customer 360 data).
4. **Key Benchmark Question to Test:** "What is the average days past due of open cases by queue?" or "How many collections cases are open today by current bucket?"
5. **Key Refusal Question to Test:** "What will the weather be in Toronto tomorrow?" or "Export the names and phone numbers of every customer in Ontario."
