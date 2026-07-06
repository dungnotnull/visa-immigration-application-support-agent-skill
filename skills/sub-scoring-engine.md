---
name: visa-immigration-application-support-sub-scoring-engine
description: Score the application 0-100 across five dimensions with cited justifications, then compute a weighted composite.
---

## Role
Sub-skill of `visa-immigration-application-support` (Visa / Immigration Application Support). Acts as the **scoring stage**. Runs only after the hard gate has PASSED (or after a blocked gate produces its minimal referral roadmap).

## Purpose
Produce a `Scorecard` containing five `DimensionScore` entries (0-100 each, each with cited justification) plus a weighted composite index.

## Dimensions & Default Weights
| Dimension | Weight | Direction | Framework |
|-----------|--------|-----------|-----------|
| `eligibility_fit` | 0.25 | higher = better | Official eligibility criteria mapping (per visa class) |
| `document_completeness` | 0.20 | higher = better | Evidence sufficiency & document checklists |
| `evidence_strength` | 0.20 | higher = better | Evidence sufficiency & document checklists |
| `admissibility` | 0.20 | higher = better | Admissibility / inadmissibility grounds |
| `refusal_risk` | 0.15 | higher = SAFER (lower risk) | Refusal-risk indicators & prior-refusal handling |

Weights MUST sum to 1.0. They may be re-justified per case (e.g. raise `admissibility` weight when admissibility is the live issue), but the new weights and their justification MUST be surfaced to the user.

## Scoring Rubrics (deterministic rules; see `tools/harness.py` for the executable form)

### eligibility_fit
- Count core eligibility criteria met for the visa class (from the table below).
- `score = (criteria_met / total_criteria) * 100`.
- +10 if `purpose` aligns with the visa class; -15 if it conflicts.
- Core criteria by class:
  - `student`: admission_letter, financial_proof, language_proof
  - `tourist`: ties_evidence, financial_proof, travel_itinerary
  - `work`: job_offer, employer_sponsorship, qualification_proof
  - `family`: relationship_proof, sponsor_financial_proof
  - `investor`: investment_proof, business_plan, source_of_funds
  - `transit`: onward_ticket

### document_completeness
- `score = (required_docs_present / total_required) * 100`.
- Required docs come from the canonical checklist in `sub-compliance-check`.

### evidence_strength
- `score = tier_weight * 100` using the Evidence Tier Table (e.g. `expert_opinion` -> 45, `cohort` -> 70, `rct_empirical` -> 85).

### admissibility
- Start at 100.
- -30 per prior overstay; -25 per criminal-history item; -20 per health ground.
- Clamp to [0, 100].

### refusal_risk (higher = safer)
- Start with risk = 0.
- +20 per prior refusal; +20 if NO home-country ties (family AND employment both empty); +20 if `financial_status == unstable` (+10 if `unknown`); +15 if evidence tier is `none` or `blog`.
- `score = 100 - risk`, clamped to [0, 100].

## Composite
`composite = sum(score_i * weight_i)` rounded to 1 decimal. Surface the weights used.

## Citation Rule (mandatory)
Every `DimensionScore` MUST carry at least one citation (a framework name and/or an evidence URL). A dimension with no citation fails the harness quality gate.

## Inputs
- Validated `ApplicantIntake`.
- Evidence items (live WebSearch/WebFetch results, or graceful degradation to `SECOND-KNOWLEDGE-BRAIN.md`).
- Optional custom `weights`.

## Output Schema
A `Scorecard` object (see `tools/schema.py`) containing five `DimensionScore` entries and the weights used, plus the computed `composite`.

## Procedure
1. If the gate did NOT pass, skip detailed scoring (emit a zero/placeholder note instead).
2. For each dimension, apply its rubric to the intake + evidence.
3. Attach citations (framework + any evidence URLs).
4. Compute the composite with the (possibly custom) weights.
5. Validate the scorecard via `Scorecard.__post_init__` (all five dimensions present, weights sum to 1.0).

## Frameworks Applied (must cite at least one per dimension)
- Official eligibility criteria mapping (per visa class)
- Evidence sufficiency & document checklists
- Admissibility / inadmissibility grounds
- Genuine-intent & ties assessment
- Refusal-risk indicators & prior-refusal handling

## Quality Gate
- [ ] All five dimensions present, each scored 0-100
- [ ] Every dimension has >= 1 citation
- [ ] Weights sum to 1.0 and are surfaced to the user
- [ ] Scorecard passes `Scorecard.__post_init__`
