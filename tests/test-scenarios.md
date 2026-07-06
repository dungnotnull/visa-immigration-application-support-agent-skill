# tests/test-scenarios.md — Visa / Immigration Application Support

These scenarios validate the `visa-immigration-application-support` harness end-to-end. Each scenario has a concrete input fixture in `tests/fixtures/<name>.json`, an expected harness behavior, and deterministic pass criteria. Run them via:

```bash
pytest tests/test_harness.py            # automated deterministic checks
python tools/harness.py --input tests/fixtures/<name>.json --output out/<name>.md
```

> Informational analysis only. These scenarios are test data, not legal advice.

---

### Scenario 1: Student visa evidence
- **Fixture:** `tests/fixtures/student_visa.json` (Vietnam -> US, student, 5/6 docs present)
- **Expected harness behavior:**
  - Intake validates; one mandatory document (`visa_application_form`) is missing but most are present, so the gate PASSES.
  - Hard gate evaluates blocking conditions FIRST; no blockers -> `passed=True`, `requires_attorney=False`.
  - Scoring covers all 5 dimensions with cited justifications; `eligibility_fit` is high (all core criteria met), `document_completeness` reflects 5/6, `evidence_strength` reflects the `expert_opinion` tier (45).
  - Roadmap prioritizes obtaining the missing form and upgrading evidence.
- **Pass criteria:** gate passes; all 5 dimensions present with citations; composite computed; roadmap has >=1 item sorted by priority; assumptions + limitations + devil's-advocate recorded.

### Scenario 2: Prior refusal handling
- **Fixture:** `tests/fixtures/prior_refusal.json` (India -> UK, student, prior SAME-class/destination refusal)
- **Expected harness behavior:**
  - Hard gate detects a prior refusal for the SAME visa class AND destination -> BLOCK + `requires_attorney=True`.
  - The referral disclaimer is emitted.
  - Only the single attorney-referral roadmap item is produced.
- **Pass criteria:** `passed=False`; `requires_attorney=True`; referral_note non-empty; roadmap has exactly 1 item (attorney referral); no detailed per-dimension plan beyond the scorecard.

### Scenario 3: Inadmissibility concern
- **Fixture:** `tests/fixtures/inadmissibility_overstay.json` (Brazil -> US, tourist, prior overstay)
- **Expected harness behavior:**
  - Hard gate detects the prior overstay -> BLOCK + `requires_attorney=True`; `admissibility_concerns` includes `overstay_history`.
  - Admissibility dimension scored low (100 - 30 = 70, but gate blocks substantive guidance).
  - Referral roadmap only.
- **Pass criteria:** `passed=False`; `requires_attorney=True`; `overstay_history` in admissibility_concerns; exactly 1 roadmap item.

### Scenario 4: Tourist visa ties
- **Fixture:** `tests/fixtures/tourist_weak_ties.json` (Philippines -> Schengen, tourist, no family/employment ties)
- **Expected harness behavior:**
  - Gate passes (no blockers; `ties_evidence` missing is a soft flag, not a blocker).
  - `refusal_risk` lowered by the weak-ties factor; admissibility and evidence moderate.
  - Roadmap includes "Document home-country ties" (effort low, impact high) near the top.
- **Pass criteria:** gate passes; `refusal_risk < 100` due to weak ties; roadmap contains a ties-strengthening item; composite computed.

### Scenario 5: Work visa eligibility
- **Fixture:** `tests/fixtures/work_visa.json` (Nigeria -> Canada, work, full docs, high evidence tier)
- **Expected harness behavior:**
  - Gate passes; all core work criteria met; `eligibility_fit` high.
  - `evidence_strength` reflects `rct_empirical` tier (85); `confidence=high`.
  - Roadmap minimal (few or no items) because the case is strong.
- **Pass criteria:** gate passes; `eligibility_fit >= 90`; `evidence_strength == 85`; roadmap items (if any) still carry effort+impact+rationale.

### Scenario 6: Blocked — no documents (regression)
- **Fixture:** `tests/fixtures/blocked_no_docs.json` (Egypt -> US, work, no documents)
- **Expected harness behavior:**
  - Hard gate detects "No mandatory documents present" -> BLOCK + attorney referral.
  - No substantive scores/plans beyond the single referral roadmap item.
- **Pass criteria:** `passed=False`; `requires_attorney=True`; blocking_conditions includes the no-docs message; exactly 1 roadmap item.

---

## Regression Checklist (run after any edit)
- [ ] Hard gate cannot be bypassed (Scenario 2/3/6 block correctly)
- [ ] Scorecard includes all 5 dimensions (Scenario 1/4/5)
- [ ] Every dimension score has >= 1 citation
- [ ] Roadmap items carry effort + impact + rationale + owner
- [ ] Roadmap sorted by priority (impact/effort) descending
- [ ] Graceful degradation when WebSearch/WebFetch unavailable (limitation stated)
- [ ] Sources section lists every citation, de-duplicated
- [ ] `assert_quality_gates(report)` passes for every passing-gate scenario
