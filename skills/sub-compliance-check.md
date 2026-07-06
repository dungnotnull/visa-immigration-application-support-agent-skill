---
name: visa-immigration-application-support-sub-compliance-check
description: HARD GATE - verify eligibility, admissibility, and required-document completeness against official rules before any output; flag where a licensed attorney is required.
---

## Role
Sub-skill of `visa-immigration-application-support` (Visa / Immigration Application Support). Acts as the **safety/risk/compliance HARD GATE**. It runs immediately after intake and BEFORE any scoring, roadmap, or substantive guidance.

## Purpose
Verify admissibility, prior-refusal handling, and required-document completeness against official frameworks; emit a `ComplianceVerdict` that either PASSES the harness or BLOCKS it with an attorney referral / disclaimer.

## Inputs
- The validated `ApplicantIntake` payload from `sub-requirements-gatherer`.
- The per-visa-class required-document checklist (canonical table below).

## Required-Document Checklist (canonical, per visa class)
| Visa class | Required documents |
|------------|--------------------|
| `student` | passport, admission_letter, financial_proof, academic_transcripts, language_proof, visa_application_form |
| `tourist` | passport, visa_application_form, financial_proof, travel_itinerary, ties_evidence, accommodation_proof |
| `work` | passport, visa_application_form, job_offer, employer_sponsorship, qualification_proof, financial_proof |
| `family` | passport, visa_application_form, relationship_proof, sponsor_financial_proof, accommodation_proof |
| `investor` | passport, visa_application_form, investment_proof, business_plan, source_of_funds |
| `transit` | passport, visa_application_form, onward_ticket |

## Blocking Conditions (any one => BLOCK + attorney referral)
1. **Prior overstay** recorded in any country (admissibility ground).
2. **Serious criminal history**: moral turpitude, controlled substance, trafficking, firearms, or violent offenses.
3. **Health grounds** of public-health concern (communicable disease of quarantine interest).
4. **Prior refusal for the SAME visa class AND destination** (re-application risk; legal review required).
5. **No mandatory documents present at all** (assessment impossible).

When any blocking condition fires: STOP, do NOT produce scores/plans, emit the referral/disclaimer, and produce only the minimal roadmap item "Resolve blocking conditions / consult a licensed immigration attorney".

## Soft-Referral Conditions (gate PASSES but referral surfaced)
- Some mandatory documents missing (the harness continues but flags them).
- Prior refusal for a DIFFERENT class/destination.
- `confidence == "low"` with admissibility-adjacent unknowns.

## Decision Output (`ComplianceVerdict`)
| Field | Type | Meaning |
|-------|------|---------|
| `passed` | bool | True only if no blocking condition fired. |
| `blocking_conditions` | list[string] | Human-readable list of tripped blockers. |
| `requires_attorney` | bool | True when any blocking or soft-referral condition fires. |
| `referral_note` | string | Standard disclaimer text when referral required. |
| `admissibility_concerns` | list[string] | Tags: `overstay_history`, `criminal_inadmissibility`, `health_inadmissibility`. |
| `missing_mandatory_documents` | list[string] | Documents still required. |
| `framework_citations` | list[string] | Frameworks used to make the decision. |

## Referral Disclaimer (verbatim when triggered)
> This assessment is informational and not legal advice. The indicators above require review by a licensed immigration attorney before filing.

## Procedure
1. Re-validate the intake payload (defensive check).
2. Evaluate each blocking condition in order; collect `blocking_conditions` and `admissibility_concerns`.
3. Compute `missing_mandatory_documents` against the checklist table.
4. Decide `passed` and `requires_attorney`.
5. Emit the `ComplianceVerdict`. If blocked, halt the harness after the verdict.

## Gate Behavior (BLOCKING — cannot be bypassed)
This sub-skill is a HARD GATE. If any blocking condition is detected:
1. STOP the harness immediately.
2. Do NOT produce scores, plans, or optimizations beyond the minimal referral roadmap item.
3. Emit the appropriate referral / disclaimer / support resource.
4. Only allow the harness to continue to scoring when `passed == True`.

## Frameworks Applied (must cite)
- Admissibility / inadmissibility grounds
- Refusal-risk indicators & prior-refusal handling
- Evidence sufficiency & document checklists

## Quality Gate
- [ ] Intake re-validated
- [ ] Every blocking condition explicitly checked (overstay, crime, health, same-class refusal, no-docs)
- [ ] `missing_mandatory_documents` computed against the canonical checklist
- [ ] Verdict emitted with `passed`, `requires_attorney`, and (if blocked) the referral note
- [ ] Gate behavior enforced downstream (scoring skipped when blocked)
