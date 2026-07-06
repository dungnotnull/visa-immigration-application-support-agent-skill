"""Deterministic regression tests for the visa-immigration-application-support harness.

These tests run without an LLM and without network access (they exercise the
deterministic core in tools/harness.py against the fixtures in tests/fixtures).
Run with: ``pytest tests/test_harness.py``.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)

from schema import (  # noqa: E402
    ApplicantIntake, SchemaError, EvidenceTier, VisaClass,
    DimensionScore, Scorecard, RoadmapItem, Effort, Impact, assert_quality_gates,
)
import harness  # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")


def load(name):
    with open(os.path.join(FIXTURES, name), "r", encoding="utf-8") as f:
        return json.load(f)


def run(name, **overrides):
    data = load(name)
    data.update(overrides)
    return harness.run(data)


# --------------------------------------------------------------------------- #
# Schema validation
# --------------------------------------------------------------------------- #
def test_intake_requires_core_fields():
    with pytest.raises(SchemaError):
        ApplicantIntake(nationality="", destination_country="US",
                        visa_class="student", purpose="x")


def test_intake_normalizes_enums_and_derives_missing():
    intake = ApplicantIntake(nationality="VN", destination_country="US",
                            visa_class="student", purpose="student - x",
                            documents_present=["passport"])
    assert isinstance(intake.visa_class, VisaClass)
    assert isinstance(intake.evidence_tier, EvidenceTier)
    # missing derived from required docs minus present
    assert "visa_application_form" in intake.documents_missing


def test_invalid_confidence_rejected():
    with pytest.raises(SchemaError):
        ApplicantIntake(nationality="VN", destination_country="US",
                        visa_class="student", purpose="x", confidence="bogus")


def test_dimension_score_requires_citation():
    with pytest.raises(SchemaError):
        DimensionScore(name="eligibility_fit", score=50, justification="x", citations=[])


def test_scorecard_requires_all_dimensions_and_unit_weights():
    with pytest.raises(SchemaError):
        Scorecard(dimensions=[
            DimensionScore(name="eligibility_fit", score=50, justification="x", citations=["f"]),
        ])


def test_roadmap_item_computes_priority():
    item = RoadmapItem(action="a", effort="low", impact="high", rationale="r")
    assert item.priority > 0
    # high impact / low effort => highest priority 3/1 = 3.0
    assert round(item.priority, 3) == 3.0


# --------------------------------------------------------------------------- #
# Scoring rubrics
# --------------------------------------------------------------------------- #
def test_eligibility_fit_full_credit_when_all_criteria_met():
    intake = ApplicantIntake(nationality="VN", destination_country="US",
                             visa_class="student", purpose="student - ms",
                             documents_present=["admission_letter", "financial_proof", "language_proof"])
    s, note, cites = harness.score_eligibility_fit(intake)
    assert s == 100.0
    assert cites  # non-empty


def test_document_completeness_ratio():
    intake = ApplicantIntake(nationality="VN", destination_country="US",
                             visa_class="student", purpose="student - ms",
                             documents_present=["passport", "admission_letter"])
    s, note, _ = harness.score_document_completeness(intake)
    # 2 of 6 required => ~33.3
    assert 30 <= s <= 40


def test_evidence_strength_tier_weight():
    intake = ApplicantIntake(nationality="VN", destination_country="US",
                             visa_class="student", purpose="student - ms",
                             evidence_tier="rct_empirical")
    s, _, _ = harness.score_evidence_strength(intake)
    assert s == 85.0


def test_refusal_risk_weak_ties_and_unstable_finances():
    intake = ApplicantIntake(nationality="PH", destination_country="Schengen",
                             visa_class="tourist", purpose="tourist - visit",
                             financial_status="unstable", family_ties_home=[],
                             employment_ties_home=[], evidence_tier="none")
    s, _, _ = harness.score_refusal_risk(intake)
    # risk = 20 (weak ties) + 20 (unstable) + 15 (none evidence) = 55 -> score 45
    assert s == 45.0


def test_admissibility_overstay_penalty():
    intake = ApplicantIntake(nationality="BR", destination_country="US",
                             visa_class="tourist", purpose="tourist - visit",
                             prior_overstays=["overstay 90d"])
    s, _, _ = harness.score_admissibility(intake)
    assert s == 70.0


# --------------------------------------------------------------------------- #
# Hard gate behavior
# --------------------------------------------------------------------------- #
def test_gate_blocks_on_overstay():
    intake = ApplicantIntake(nationality="BR", destination_country="US",
                             visa_class="tourist", purpose="tourist - visit",
                             prior_overstays=["overstay"], documents_present=["passport"])
    v = harness.run_compliance_gate(intake)
    assert v.passed is False
    assert v.requires_attorney is True
    assert "overstay_history" in v.admissibility_concerns


def test_gate_blocks_on_serious_crime():
    intake = ApplicantIntake(nationality="X", destination_country="US",
                             visa_class="tourist", purpose="tourist - visit",
                             criminal_history=["controlled_substance offense"],
                             documents_present=["passport"])
    v = harness.run_compliance_gate(intake)
    assert v.passed is False and v.requires_attorney is True


def test_gate_blocks_on_same_class_destination_refusal():
    intake = ApplicantIntake(nationality="IN", destination_country="United Kingdom",
                             visa_class="student", purpose="student - pg",
                             prior_refusals=["student visa refusal for United Kingdom 2024"],
                             documents_present=["passport", "admission_letter"])
    v = harness.run_compliance_gate(intake)
    assert v.passed is False and v.requires_attorney is True


def test_gate_blocks_on_no_documents():
    intake = ApplicantIntake(nationality="EG", destination_country="US",
                             visa_class="work", purpose="work - seasonal",
                             documents_present=[])
    v = harness.run_compliance_gate(intake)
    assert v.passed is False
    assert any("mandatory documents" in b for b in v.blocking_conditions)


def test_gate_passes_clean_case():
    intake = ApplicantIntake(nationality="NG", destination_country="Canada",
                             visa_class="work", purpose="work - sde",
                             documents_present=["passport", "visa_application_form", "job_offer",
                                                "employer_sponsorship", "qualification_proof",
                                                "financial_proof"])
    v = harness.run_compliance_gate(intake)
    assert v.passed is True
    assert v.requires_attorney is False


# --------------------------------------------------------------------------- #
# End-to-end scenarios (fixtures)
# --------------------------------------------------------------------------- #
def assert_valid_report(report):
    # quality gates enforced inside run(); if we reach here it passed.
    assert report.composite_score == report.scorecard.composite
    assert len(report.scorecard.dimensions) == 5
    assert all(d.citations for d in report.scorecard.dimensions)
    assert report.devils_advocate_notes
    assert report.sources


def test_scenario_1_student_visa():
    r = run("student_visa.json")
    assert r.compliance_verdict.passed is True
    assert r.compliance_verdict.requires_attorney is False
    assert any("visa_application_form" in i.action for i in r.roadmap)
    assert_valid_report(r)


def test_scenario_2_prior_refusal_blocks():
    r = run("prior_refusal.json")
    assert r.compliance_verdict.passed is False
    assert r.compliance_verdict.requires_attorney is True
    assert r.compliance_verdict.referral_note
    assert len(r.roadmap) == 1
    assert_valid_report(r)


def test_scenario_3_overstay_blocks():
    r = run("inadmissibility_overstay.json")
    assert r.compliance_verdict.passed is False
    assert "overstay_history" in r.compliance_verdict.admissibility_concerns
    assert len(r.roadmap) == 1
    assert_valid_report(r)


def test_scenario_4_weak_ties_roadmap():
    r = run("tourist_weak_ties.json")
    assert r.compliance_verdict.passed is True
    assert any("ties" in i.action.lower() for i in r.roadmap)
    # refusal_risk reduced by weak ties
    rr = next(d for d in r.scorecard.dimensions if d.name == "refusal_risk")
    assert rr.score < 100
    assert_valid_report(r)


def test_scenario_5_work_visa_strong():
    r = run("work_visa.json")
    assert r.compliance_verdict.passed is True
    elig = next(d for d in r.scorecard.dimensions if d.name == "eligibility_fit")
    assert elig.score >= 90
    ev = next(d for d in r.scorecard.dimensions if d.name == "evidence_strength")
    assert ev.score == 85.0
    assert_valid_report(r)


def test_scenario_6_no_docs_blocks():
    r = run("blocked_no_docs.json")
    assert r.compliance_verdict.passed is False
    assert r.compliance_verdict.requires_attorney is True
    assert len(r.roadmap) == 1
    assert_valid_report(r)


# --------------------------------------------------------------------------- #
# Roadmap prioritization & dedup
# --------------------------------------------------------------------------- #
def test_roadmap_sorted_by_priority_and_dedup():
    r = run("tourist_weak_ties.json")
    priorities = [i.priority for i in r.roadmap]
    assert priorities == sorted(priorities, reverse=True)
    assert len({i.action for i in r.roadmap}) == len(r.roadmap)


# --------------------------------------------------------------------------- #
# Graceful degradation
# --------------------------------------------------------------------------- #
def test_graceful_degradation_records_limitation():
    r = run("student_visa.json")
    assert any("SECOND-KNOWLEDGE-BRAIN.md" in lim for lim in r.limitations)


def test_live_evidence_callback_used():
    calls = {"n": 0}

    def fake_ev(intake):
        calls["n"] += 1
        return [{"title": "Live USCIS guidance", "url": "https://example.gov/x", "tier": "cohort"}]

    r = harness.run(load("student_visa.json"), evidence_fn=fake_ev)
    assert calls["n"] == 1
    # limitation about degradation should NOT appear
    assert not any("SECOND-KNOWLEDGE-BRAIN" in lim for lim in r.limitations)
    # live url present in sources
    assert "https://example.gov/x" in r.sources


# --------------------------------------------------------------------------- #
# Markdown rendering
# --------------------------------------------------------------------------- #
def test_render_markdown_has_all_sections():
    r = run("student_visa.json")
    md = harness.render_markdown(r)
    for section in ["## 1. Summary", "## 2. Compliance Gate Verdict", "## 3. Scorecard",
                    "## 4. Improvement Roadmap", "## 5. Assumptions, Confidence & Limitations",
                    "## 6. Devil's-Advocate Review", "## 7. Sources",
                    "NOT legal advice"]:
        assert section in md


# --------------------------------------------------------------------------- #
# CLI smoke
# --------------------------------------------------------------------------- #
def test_cli_writes_report(tmp_path):
    from harness import main
    out = tmp_path / "r.md"
    rc = main(["--input", os.path.join(FIXTURES, "student_visa.json"),
               "--output", str(out)])
    assert rc == 0
    assert out.exists()
    assert "## 3. Scorecard" in out.read_text(encoding="utf-8")
