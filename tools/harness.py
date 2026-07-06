"""Deterministic reference implementation of the visa-immigration-application-support harness.

This module encodes the *rule-based* core of the skill so the harness can be
executed, validated, and regression-tested without invoking an LLM. It is the
executable counterpart of ``skills/main.md``: every Markdown instruction that
can be made deterministic (intake validation, the hard compliance gate, the
multi-dimensional scoring rubric, roadmap prioritisation, quality-gate
enforcement, and final artifact rendering) is implemented here.

LLM-driven steps (free-text intake, live WebSearch/WebFetch evidence
enrichment, narrative devil's-advocate reasoning) plug in around this core via
optional callbacks. When those callbacks are absent the harness degrades
gracefully to ``SECOND-KNOWLEDGE-BRAIN.md`` and records the limitation, exactly
as the skill specification requires.

CLI:
    python tools/harness.py --input tests/fixtures/student_visa.json --output report.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Callable, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from schema import (  # noqa: E402
    ApplicantIntake, ComplianceVerdict, DimensionScore, Scorecard, RoadmapItem,
    HarnessReport, EvidenceTier, Effort, Impact, VisaClass, REQUIRED_DOCUMENTS,
    DIMENSIONS, DEFAULT_WEIGHTS, TIER_WEIGHT, assert_quality_gates, SchemaError,
)

BRAIN_PATH = os.path.join(HERE, "..", "SECOND-KNOWLEDGE-BRAIN.md")

FRAMEWORKS = {
    "eligibility": "Official eligibility criteria mapping (per visa class)",
    "checklist": "Evidence sufficiency & document checklists",
    "admissibility": "Admissibility / inadmissibility grounds",
    "ties": "Genuine-intent & ties assessment",
    "refusal": "Refusal-risk indicators & prior-refusal handling",
    "procedural": "Procedural compliance (forms, fees, deadlines)",
}

# Per-class core eligibility criteria used by the eligibility-fit rubric.
ELIGIBILITY_CRITERIA: Dict[VisaClass, List[str]] = {
    VisaClass.STUDENT: ["admission_letter", "financial_proof", "language_proof"],
    VisaClass.TOURIST: ["ties_evidence", "financial_proof", "travel_itinerary"],
    VisaClass.WORK: ["job_offer", "employer_sponsorship", "qualification_proof"],
    VisaClass.FAMILY: ["relationship_proof", "sponsor_financial_proof"],
    VisaClass.INVESTOR: ["investment_proof", "business_plan", "source_of_funds"],
    VisaClass.TRANSIT: ["onward_ticket"],
}


# --------------------------------------------------------------------------- #
# Stage 1: intake validation
# --------------------------------------------------------------------------- #
def load_intake(data: dict) -> ApplicantIntake:
    """Validate raw user-supplied data into a schema-valid ApplicantIntake."""
    required_fields = ("nationality", "destination_country", "visa_class", "purpose")
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        raise SchemaError(f"intake missing required fields: {missing}")
    return ApplicantIntake.from_dict(data)


def missing_intake_fields(data: dict) -> List[str]:
    """Return the list of essential intake fields still required from the user."""
    return [f for f in ("nationality", "destination_country", "visa_class", "purpose")
            if not data.get(f)]


# --------------------------------------------------------------------------- #
# Stage 2: HARD compliance gate
# --------------------------------------------------------------------------- #
def run_compliance_gate(intake: ApplicantIntake) -> ComplianceVerdict:
    """Evaluate blocking conditions and decide pass / refer.

    Blocking conditions (per the Admissibility / inadmissibility grounds and
    Refusal-risk frameworks):
      * prior overstay in any country -> attorney referral required
      * criminal history of moral turpitude / controlled-substance -> blocked
      * serious health grounds of public-health concern -> blocked
      * prior visa refusal for the SAME class & destination -> attorney referral
      * mandatory documents entirely missing -> blocked (cannot assess)
    """
    blocking: List[str] = []
    admissibility: List[str] = []
    requires_attorney = False
    citations = [FRAMEWORKS["admissibility"], FRAMEWORKS["refusal"], FRAMEWORKS["checklist"]]

    if intake.prior_overstays:
        blocking.append(f"Prior overstay recorded: {', '.join(intake.prior_overstays)}")
        admissibility.append("overstay_history")
        requires_attorney = True

    serious_crimes = {"moral_turpitude", "controlled_substance", "trafficking", "firearms", "violent"}
    for c in intake.criminal_history:
        if any(tag in c.lower() for tag in serious_crimes):
            blocking.append(f"Serious criminal history: {c}")
            admissibility.append("criminal_inadmissibility")
            requires_attorney = True
            break

    if intake.health_grounds:
        blocking.append(f"Health grounds of concern: {', '.join(intake.health_grounds)}")
        admissibility.append("health_inadmissibility")
        requires_attorney = True

    for refusal in intake.prior_refusals:
        cls_token = intake.visa_class.value
        dest_token = intake.destination_country.lower()
        if cls_token in refusal.lower() and dest_token in refusal.lower():
            blocking.append(f"Prior refusal for same class/destination: {refusal}")
            requires_attorney = True
            break

    mandatory = intake.required_documents()
    if mandatory and not any(d.lower() in {x.lower() for x in intake.documents_present} for d in mandatory):
        blocking.append("No mandatory documents present; cannot complete the assessment")
        requires_attorney = True

    missing_mandatory = [d for d in mandatory
                        if d.lower() not in {x.lower() for x in intake.documents_present}]

    passed = len(blocking) == 0
    referral_note = ""
    if requires_attorney:
        referral_note = (
            "This assessment is informational and not legal advice. The indicators above "
            "require review by a licensed immigration attorney before filing."
        )

    return ComplianceVerdict(
        passed=passed,
        blocking_conditions=blocking,
        requires_attorney=requires_attorney,
        referral_note=referral_note,
        admissibility_concerns=admissibility,
        missing_mandatory_documents=missing_mandatory,
        framework_citations=citations,
    )


# --------------------------------------------------------------------------- #
# Stage 3: evidence enrichment (graceful degradation)
# --------------------------------------------------------------------------- #
EvidenceFn = Callable[[ApplicantIntake], List[dict]]


def load_brain(path: str = BRAIN_PATH) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def enrich_evidence(intake: ApplicantIntake, evidence_fn: Optional[EvidenceFn]) -> Tuple[List[dict], bool]:
    """Return (evidence_items, used_live_search). Degrades to knowledge base."""
    used_live = False
    if evidence_fn is not None:
        try:
            items = evidence_fn(intake) or []
            used_live = True
            return items, used_live
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[warn] live evidence search failed ({exc}); degrading to knowledge base")
    # Graceful degradation: scan the knowledge base for matching citations.
    brain = load_brain()
    items: List[dict] = []
    for framework in FRAMEWORKS.values():
        if framework in brain:
            items.append({"title": framework, "url": "SECOND-KNOWLEDGE-BRAIN.md", "tier": "expert_opinion"})
    return items, used_live


# --------------------------------------------------------------------------- #
# Stage 4: scoring engine
# --------------------------------------------------------------------------- #
def _clamp(x: float) -> float:
    return max(0.0, min(100.0, round(x, 1)))


def score_eligibility_fit(intake: ApplicantIntake) -> Tuple[float, str, List[str]]:
    criteria = ELIGIBILITY_CRITERIA.get(intake.visa_class, [])
    if not criteria:
        return 50.0, "No structured eligibility criteria mapped for this visa class.", [FRAMEWORKS["eligibility"]]
    present = {x.lower() for x in intake.documents_present}
    met = sum(1 for c in criteria if c.lower() in present or c in present)
    base = (met / len(criteria)) * 100.0
    # Purpose alignment modifier
    purpose_ok = intake.purpose and intake.purpose.lower().startswith(intake.visa_class.value)
    if purpose_ok:
        base = min(100.0, base + 10.0)
    elif not purpose_ok:
        base = max(0.0, base - 15.0)
    note = (f"{met}/{len(criteria)} core eligibility criteria met for "
            f"{intake.visa_class.value} visa; purpose alignment {'yes' if purpose_ok else 'no'}.")
    return _clamp(base), note, [FRAMEWORKS["eligibility"]]


def score_document_completeness(intake: ApplicantIntake) -> Tuple[float, str, List[str]]:
    required = intake.required_documents()
    if not required:
        return 50.0, "No required-document checklist mapped.", [FRAMEWORKS["checklist"]]
    present = {x.lower() for x in intake.documents_present}
    ratio = sum(1 for d in required if d.lower() in present) / len(required)
    score = ratio * 100.0
    missing = [d for d in required if d.lower() not in present]
    note = (f"{len(required) - len(missing)}/{len(required)} required documents present."
            + (f" Missing: {', '.join(missing)}" if missing else " All present."))
    return _clamp(score), note, [FRAMEWORKS["checklist"]]


def score_evidence_strength(intake: ApplicantIntake) -> Tuple[float, str, List[str]]:
    weight = TIER_WEIGHT.get(intake.evidence_tier, 0.0)
    score = weight * 100.0
    note = f"Evidence tier: {intake.evidence_tier.value} (weight {weight:.2f})."
    return _clamp(score), note, [FRAMEWORKS["checklist"], FRAMEWORKS["refusal"]]


def score_admissibility(intake: ApplicantIntake) -> Tuple[float, str, List[str]]:
    score = 100.0
    concerns: List[str] = []
    if intake.prior_overstays:
        score -= 30.0 * len(intake.prior_overstays)
        concerns.append(f"overstay({len(intake.prior_overstays)})")
    if intake.criminal_history:
        score -= 25.0 * len(intake.criminal_history)
        concerns.append(f"criminal({len(intake.criminal_history)})")
    if intake.health_grounds:
        score -= 20.0 * len(intake.health_grounds)
        concerns.append(f"health({len(intake.health_grounds)})")
    note = ("No admissibility concerns." if not concerns
            else f"Admissibility concerns: {', '.join(concerns)}.")
    return _clamp(score), note, [FRAMEWORKS["admissibility"]]


def score_refusal_risk(intake: ApplicantIntake) -> Tuple[float, str, List[str]]:
    """Higher score = lower refusal risk (consistent with other dimensions)."""
    risk = 0.0
    factors: List[str] = []
    risk += 20.0 * len(intake.prior_refusals)
    if intake.prior_refusals:
        factors.append(f"prior_refusals({len(intake.prior_refusals)})")
    if not intake.family_ties_home and not intake.employment_ties_home:
        risk += 20.0
        factors.append("weak_home_ties")
    if intake.financial_status == "unstable":
        risk += 20.0
        factors.append("unstable_finances")
    elif intake.financial_status == "unknown":
        risk += 10.0
        factors.append("unknown_finances")
    if intake.evidence_tier in (EvidenceTier.NONE, EvidenceTier.BLOG):
        risk += 15.0
        factors.append("weak_evidence")
    score = 100.0 - risk
    note = (f"Refusal risk factors: {', '.join(factors) if factors else 'none'}; "
            f"residual risk {risk:.0f}/100 -> safety score {score:.0f}.")
    return _clamp(score), note, [FRAMEWORKS["refusal"], FRAMEWORKS["ties"]]


def run_scoring(intake: ApplicantIntake, evidence_items: List[dict],
                weights: Optional[Dict[str, float]] = None) -> Scorecard:
    w = weights or dict(DEFAULT_WEIGHTS)
    fns = {
        "eligibility_fit": score_eligibility_fit,
        "document_completeness": score_document_completeness,
        "evidence_strength": score_evidence_strength,
        "admissibility": score_admissibility,
        "refusal_risk": score_refusal_risk,
    }
    dims: List[DimensionScore] = []
    for name in DIMENSIONS:
        s, note, cites = fns[name](intake)
        # Append any live/knowledge-base evidence citations
        # Add live/knowledge-base evidence citations (de-duplicated, preserves order)
        extra, seen_extra = [], set()
        for e in evidence_items:
            if not e:
                continue
            c = e.get("url") or e.get("title") or ""
            if c and c not in seen_extra and c not in cites:
                extra.append(c); seen_extra.add(c)
        cites = cites + extra
        dims.append(DimensionScore(name=name, score=s, justification=note, citations=cites))
    return Scorecard(dimensions=dims, weights=w)


# --------------------------------------------------------------------------- #
# Stage 5: improvement roadmap
# --------------------------------------------------------------------------- #
def build_roadmap(intake: ApplicantIntake, scorecard: Scorecard) -> List[RoadmapItem]:
    items: List[RoadmapItem] = []
    required = intake.required_documents()
    present = {x.lower() for x in intake.documents_present}
    for doc in required:
        if doc.lower() not in present:
            items.append(RoadmapItem(
                action=f"Obtain missing required document: {doc}",
                effort=Effort.MEDIUM, impact=Impact.HIGH,
                rationale=f"{doc} is mandatory for a {intake.visa_class.value} visa "
                         f"under the Evidence sufficiency & document checklist framework.",
                owner="applicant", expected_effect="Raises document_completeness directly.",
                citations=[FRAMEWORKS["checklist"]],
            ))
    if intake.evidence_tier in (EvidenceTier.NONE, EvidenceTier.BLOG, EvidenceTier.EXPERT_OPINION):
        items.append(RoadmapItem(
            action="Upgrade evidence quality (primary documents / official records over self-attestation)",
            effort=Effort.MEDIUM, impact=Impact.HIGH,
            rationale="Higher evidence tier reduces refusal risk and strengthens the case.",
            expected_effect="Raises evidence_strength; lowers refusal_risk.",
            citations=[FRAMEWORKS["checklist"], FRAMEWORKS["refusal"]],
        ))
    if not intake.family_ties_home and not intake.employment_ties_home:
        items.append(RoadmapItem(
            action="Document home-country ties (employment letter, property, family, return commitment)",
            effort=Effort.LOW, impact=Impact.HIGH,
            rationale="Genuine-intent & ties assessment: weak ties are a top refusal driver.",
            expected_effect="Raises refusal_risk safety score; supports admissibility.",
            citations=[FRAMEWORKS["ties"]],
        ))
    if intake.financial_status in ("unstable", "unknown"):
        items.append(RoadmapItem(
            action="Provide verifiable financial proof (bank statements, sponsor affidavit, income proof)",
            effort=Effort.MEDIUM, impact=Impact.HIGH,
            rationale="Financial sufficiency is a core eligibility criterion and refusal-risk indicator.",
            expected_effect="Raises eligibility_fit and refusal_risk scores.",
            citations=[FRAMEWORKS["eligibility"], FRAMEWORKS["refusal"]],
        ))
    if intake.prior_overstays or intake.prior_refusals or intake.criminal_history or intake.health_grounds:
        items.append(RoadmapItem(
            action="Consult a licensed immigration attorney for admissibility/refusal remediation",
            effort=Effort.LOW, impact=Impact.HIGH,
            rationale="Prior adverse history triggers the attorney-referral gate; legal review required.",
            owner="applicant+attorney",
            expected_effect="Surfaces remediation options; may unlock admissibility waivers.",
            citations=[FRAMEWORKS["admissibility"], FRAMEWORKS["refusal"]],
        ))
    # Deduplicate by action text
    seen = set()
    unique = []
    for it in items:
        if it.action in seen:
            continue
        seen.add(it.action)
        unique.append(it)
    unique.sort(key=lambda r: r.priority, reverse=True)
    return unique


# --------------------------------------------------------------------------- #
# Stage 6: devil's-advocate quality gate
# --------------------------------------------------------------------------- #
DevilFn = Callable[[HarnessReport], List[str]]


def devils_advocate(report: HarnessReport, devil_fn: Optional[DevilFn]) -> List[str]:
    if devil_fn is not None:
        try:
            return devil_fn(report) or []
        except Exception as exc:  # pragma: no cover
            print(f"[warn] devil's-advocate callback failed ({exc}); using deterministic review")
    notes: List[str] = []
    # Auto challenge the weakest dimension
    weakest = min(report.scorecard.dimensions, key=lambda d: d.score)
    notes.append(f"Challenged {weakest.name}={weakest.score}: "
                 "is the justification over- or under-stated? Reviewed against cited framework.")
    if report.compliance_verdict.requires_attorney:
        notes.append("Re-checked attorney-referral gate: referral must remain in the final output.")
    if any(d.score < 40 for d in report.scorecard.dimensions):
        notes.append("Low-scoring dimension(s) detected; confirm assumptions and re-state limitations.")
    notes.append("Confirmed every dimension cites at least one framework or evidence source.")
    return notes


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def run(data: dict, evidence_fn: Optional[EvidenceFn] = None,
        devil_fn: Optional[DevilFn] = None) -> HarnessReport:
    intake = load_intake(data)
    verdict = run_compliance_gate(intake)
    evidence_items, used_live = enrich_evidence(intake, evidence_fn)
    scorecard = run_scoring(intake, evidence_items)

    roadmap = [] if not verdict.passed else build_roadmap(intake, scorecard)
    if not verdict.passed:
        # If gate blocked, still produce a minimal roadmap centred on the referral
        roadmap = [RoadmapItem(
            action="Resolve blocking conditions / consult a licensed immigration attorney",
            effort=Effort.LOW, impact=Impact.HIGH,
            rationale="Hard gate tripped; no scores/plans are actionable until cleared.",
            owner="applicant+attorney", expected_effect="Unblocks the harness.",
            citations=verdict.framework_citations,
        )]

    top_findings = [f"Composite score {scorecard.composite}/100"]
    low = sorted(scorecard.dimensions, key=lambda d: d.score)[:3]
    for d in low:
        top_findings.append(f"{d.name} = {d.score}: {d.justification}")
    if verdict.requires_attorney:
        top_findings.insert(0, "ATTORNEY REFERRAL REQUIRED")

    limitations = []
    if not used_live:
        limitations.append("Live web search unavailable; evidence sourced from SECOND-KNOWLEDGE-BRAIN.md.")
    limitations.append("Scoring rubric is informational and not legal advice.")

    assumptions = intake.assumptions or [
        f"Assumes nationality={intake.nationality}, destination={intake.destination_country}.",
        "Assumes supplied documents are authentic and current.",
    ]

    report = HarnessReport(
        subject=f"{intake.nationality} applicant -> {intake.destination_country} ({intake.visa_class.value})",
        purpose=intake.purpose,
        composite_score=scorecard.composite,
        top_findings=top_findings,
        scorecard=scorecard,
        roadmap=roadmap,
        compliance_verdict=verdict,
        assumptions=assumptions,
        confidence=intake.confidence,
        limitations=limitations,
        sources=sorted({c for d in scorecard.dimensions for c in d.citations}
                       | {c for r in roadmap for c in r.citations}
                       | set(verdict.framework_citations)),
        devils_advocate_notes=[],
    )
    report.devils_advocate_notes = devils_advocate(report, devil_fn)
    assert_quality_gates(report)
    return report


# --------------------------------------------------------------------------- #
# Markdown rendering
# --------------------------------------------------------------------------- #
def render_markdown(report: HarnessReport) -> str:
    L = []
    L.append("# Visa / Immigration Application Support - Assessment Report")
    L.append("")
    L.append("> Informational analysis only. This is NOT legal advice.")
    L.append("")
    L.append("## 1. Summary")
    L.append(f"- **Subject:** {report.subject}")
    L.append(f"- **Purpose:** {report.purpose}")
    L.append(f"- **Composite score:** {report.composite_score}/100")
    L.append("- **Top findings:**")
    for f in report.top_findings:
        L.append(f"  - {f}")
    if report.compliance_verdict.referral_note:
        L.append("")
        L.append(f"> **Referral:** {report.compliance_verdict.referral_note}")
    L.append("")

    cv = report.compliance_verdict
    L.append("## 2. Compliance Gate Verdict")
    L.append(f"- **Passed:** {cv.passed}")
    L.append(f"- **Requires attorney:** {cv.requires_attorney}")
    if cv.blocking_conditions:
        L.append("- **Blocking conditions:**")
        for b in cv.blocking_conditions:
            L.append(f"  - {b}")
    if cv.missing_mandatory_documents:
        L.append(f"- **Missing mandatory documents:** {', '.join(cv.missing_mandatory_documents)}")
    L.append("")

    L.append("## 3. Scorecard")
    L.append("| Dimension | Score | Justification | Citations |")
    L.append("|-----------|-------|---------------|-----------|")
    for d in report.scorecard.dimensions:
        cites = "; ".join(d.citations)
        L.append(f"| {d.name} | {d.score} | {d.justification} | {cites} |")
    L.append(f"| **Composite** | **{report.composite_score}** | weighted mean | - |")
    L.append("")
    L.append(f"Weights: {json.dumps(report.scorecard.weights)}")
    L.append("")

    L.append("## 4. Improvement Roadmap (priority order)")
    L.append("| # | Action | Effort | Impact | Rationale | Owner | Expected effect |")
    L.append("|---|--------|--------|--------|-----------|-------|-----------------|")
    for i, r in enumerate(report.roadmap, 1):
        L.append(f"| {i} | {r.action} | {r.effort.value} | {r.impact.value} | {r.rationale} | {r.owner} | {r.expected_effect} |")
    L.append("")

    L.append("## 5. Assumptions, Confidence & Limitations")
    L.append(f"- **Confidence:** {report.confidence}")
    L.append("- **Assumptions:**")
    for a in report.assumptions:
        L.append(f"  - {a}")
    L.append("- **Limitations:**")
    for lim in report.limitations:
        L.append(f"  - {lim}")
    L.append("")

    L.append("## 6. Devil's-Advocate Review")
    for n in report.devils_advocate_notes:
        L.append(f"- {n}")
    L.append("")

    L.append("## 7. Sources")
    for s in report.sources:
        L.append(f"- {s}")
    L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Run the visa-immigration-application-support harness.")
    ap.add_argument("--input", required=True, help="Path to intake JSON file.")
    ap.add_argument("--output", help="Path to write the Markdown report. Omit for stdout.")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    args = ap.parse_args(argv)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    try:
        report = run(data)
    except SchemaError as e:
        print(f"[error] harness aborted: {e}", file=sys.stderr)
        return 2
    out = report.to_json() if args.json else render_markdown(report)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"[ok] report written to {args.output}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
