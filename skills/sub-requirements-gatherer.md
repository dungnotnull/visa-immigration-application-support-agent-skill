---
name: visa-immigration-application-support-sub-requirements-gatherer
description: Capture nationality, visa class, destination country, purpose, and history into a schema-valid intake payload.
---

## Role
Sub-skill of `visa-immigration-application-support` (Visa / Immigration Application Support). Acts as the **pre-gate screener / intake stage**. It must complete before any compliance, scoring, or roadmap work begins.

## Purpose
Capture the structured applicant inputs required by every downstream stage and produce a single schema-valid `ApplicantIntake` payload. Informational only — never legal advice.

## Required Fields (hard-required)
| Field | Type | Notes |
|-------|------|-------|
| `nationality` | string | Applicant's current citizenship. |
| `destination_country` | string | Country of application/entry. |
| `visa_class` | enum | One of: `student`, `tourist`, `work`, `family`, `investor`, `transit`. |
| `purpose` | string | Free-text purpose; SHOULD start with the visa class token (e.g. `student - ...`). |

## Optional but Strongly Requested Fields
| Field | Type | Default | Used by |
|-------|------|---------|---------|
| `travel_history` | list[string] | `[]` | admissibility, refusal risk |
| `prior_refusals` | list[string] | `[]` | refusal risk, attorney gate |
| `prior_overstays` | list[string] | `[]` | admissibility (hard) |
| `criminal_history` | list[string] | `[]` | admissibility (hard) |
| `health_grounds` | list[string] | `[]` | admissibility (hard) |
| `family_ties_home` | list[string] | `[]` | genuine-intent / refusal risk |
| `employment_ties_home` | list[string] | `[]` | genuine-intent / refusal risk |
| `financial_status` | enum `stable`/`unstable`/`unknown` | `unknown` | eligibility, refusal risk |
| `documents_present` | list[string] | `[]` | document completeness |
| `documents_missing` | list[string] | derived | document completeness |
| `evidence_tier` | enum (see tier table) | `none` | evidence strength |
| `evidence_summary` | string | `""` | narrative |
| `assumptions` | list[string] | `[]` | quality gate |
| `confidence` | enum `low`/`medium`/`high` | `medium` | quality gate |

## Evidence Tier Table (highest -> lowest)
| Value | Weight | Examples |
|-------|--------|----------|
| `systematic_review` | 1.00 | Cochrane/PMC systematic reviews of migration decisions |
| `meta_analysis` | 0.95 | Meta-analyses of refusal-rate predictors |
| `rct_empirical` | 0.85 | Government empirical evaluation reports, RCT-style pilots |
| `cohort` | 0.70 | Cohort studies of visa outcomes |
| `expert_opinion` | 0.45 | AILA practice materials, official guidance commentary |
| `blog` | 0.20 | Non-authoritative blog posts (weak) |
| `none` | 0.00 | No evidence supplied |

## Procedure
1. Read the user request and any supplied artifacts. Identify hard-required fields.
2. For every missing hard-required field, ask a single targeted question (batch up to 4 at once to respect the user's time). Do NOT proceed to scoring until all four are present.
3. For optional fields, request them once; if the user declines, record `unknown`/empty and lower `confidence`.
4. Normalize `visa_class` and `evidence_tier` to the enum values above. Map `documents_missing` from the per-class checklist (see `sub-compliance-check`) when the user does not supply it.
5. Build the `ApplicantIntake` payload (JSON-shaped). Validate it against the schema (see `tools/schema.py` `ApplicantIntake`).
6. Record explicit `assumptions` and a `confidence` rating. Lower confidence whenever a key field is unknown.

## Output Schema
A single JSON object conforming to `ApplicantIntake` (see `tools/schema.py`). Example:
```json
{
  "nationality": "Vietnam",
  "destination_country": "United States",
  "visa_class": "student",
  "purpose": "student - pursue a Master's degree",
  "documents_present": ["passport", "admission_letter", "financial_proof", "academic_transcripts", "language_proof"],
  "documents_missing": ["visa_application_form"],
  "evidence_tier": "expert_opinion",
  "financial_status": "stable",
  "family_ties_home": ["parents"],
  "employment_ties_home": [],
  "prior_refusals": [],
  "prior_overstays": [],
  "criminal_history": [],
  "health_grounds": [],
  "assumptions": ["Applicant intends to return after studies."],
  "confidence": "medium"
}
```

## Frameworks Applied (must cite)
- Official eligibility criteria mapping (per visa class)
- Evidence sufficiency & document checklists
- Admissibility / inadmissibility grounds
- Genuine-intent & ties assessment

## Quality Gate
- [ ] All four hard-required fields present and non-empty
- [ ] `visa_class` and `evidence_tier` normalized to enum values
- [ ] `documents_missing` derived or explicitly supplied
- [ ] Assumptions and confidence recorded
- [ ] Output passes `ApplicantIntake.__post_init__` validation (run `tools/schema.py`)
