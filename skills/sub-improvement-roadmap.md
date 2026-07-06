---
name: visa-immigration-application-support-sub-improvement-roadmap
description: Produce a prioritized improvement roadmap (effort x impact) of documents, evidence, and statements ranked by refusal-risk reduction.
---

## Role
Sub-skill of `visa-immigration-application-support` (Visa / Immigration Application Support). Acts as the **roadmap stage**, producing the actionable artifact that follows the scorecard.

## Purpose
Recommend concrete documents, evidence upgrades, and statements to strengthen the application, ranked by refusal-risk reduction. Every item carries an `effort`, an `impact`, a `rationale`, an `owner`, and an `expected_effect`.

## Prioritization Model
Priority is `impact_rank / effort_rank` (higher = more urgent):
- `effort`: `low` = 1, `medium` = 2, `high` = 3
- `impact`: `low` = 1, `medium` = 2, `high` = 3
Items are sorted by `priority` descending. Ties keep a stable order.

## Item Schema (`RoadmapItem`)
| Field | Type | Rule |
|-------|------|------|
| `action` | string | Concrete, single action. |
| `effort` | enum `low`/`medium`/`high` | Required. |
| `impact` | enum `low`/`medium`/`high` | Required. |
| `rationale` | string | Required; cites a framework. |
| `owner` | string | Default `applicant`; `applicant+attorney` when legal review needed. |
| `expected_effect` | string | Which dimension(s) it improves. |
| `citations` | list[string] | Framework(s) / evidence justifying the item. |

## Standard Item Templates (generated from the intake)
1. **Missing required document** — `Obtain missing required document: <doc>` — effort `medium`, impact `high`. Cites the Evidence sufficiency & document checklist framework.
2. **Weak evidence** — `Upgrade evidence quality (primary documents / official records over self-attestation)` — effort `medium`, impact `high`. Cites Evidence sufficiency & Refusal-risk frameworks.
3. **Weak ties** (no family AND no employment ties) — `Document home-country ties (employment letter, property, family, return commitment)` — effort `low`, impact `high`. Cites Genuine-intent & ties assessment.
4. **Unstable/unknown finances** — `Provide verifiable financial proof (bank statements, sponsor affidavit, income proof)` — effort `medium`, impact `high`. Cites Eligibility & Refusal-risk frameworks.
5. **Adverse history** (overstay / refusal / crime / health) — `Consult a licensed immigration attorney for admissibility/refusal remediation` — effort `low`, impact `high`, owner `applicant+attorney`. Cites Admissibility & Refusal-risk frameworks.

When the hard gate is BLOCKED, emit ONLY the single item: `Resolve blocking conditions / consult a licensed immigration attorney` (effort `low`, impact `high`, owner `applicant+attorney`).

## Procedure
1. If the gate did not pass, emit the single referral roadmap item and stop.
2. Otherwise, generate items from the intake (missing docs, weak evidence, weak ties, finances, adverse history).
3. De-duplicate by `action` text (keep first occurrence).
4. Sort by `priority` descending.
5. Validate each item via `RoadmapItem.__post_init__`.

## Inputs
- Validated `ApplicantIntake`.
- `Scorecard` from `sub-scoring-engine`.
- `ComplianceVerdict` (to know whether the gate passed).

## Output Schema
A list of `RoadmapItem` objects (see `tools/schema.py`).

## Frameworks Applied (must cite per item)
- Evidence sufficiency & document checklists
- Genuine-intent & ties assessment
- Refusal-risk indicators & prior-refusal handling
- Admissibility / inadmissibility grounds
- Official eligibility criteria mapping (per visa class)

## Quality Gate
- [ ] Every item has `action`, `effort`, `impact`, `rationale`, `owner`, `expected_effect`
- [ ] Items sorted by priority (impact / effort) descending
- [ ] No duplicate `action` text
- [ ] Blocked-gate case emits exactly the single attorney-referral item
