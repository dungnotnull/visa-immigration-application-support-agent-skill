"""Shared data schemas for the visa-immigration-application-support harness.

These dataclasses encode the structured payloads that flow between the
skill's sub-stages (intake -> compliance gate -> scoring -> roadmap ->
report). They are the single source of truth for both the Markdown skill
instructions and the deterministic reference implementation in
``tools/harness.py`` so the skill can be executed and tested without an LLM.

All schemas are plain dataclasses (no third-party deps) and validate on
construction via ``__post_init__`` so that malformed inputs fail fast with a
clear ``SchemaError`` rather than propagating silently.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional
import json


class SchemaError(ValueError):
    """Raised when a payload violates the harness schema."""


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class VisaClass(str, Enum):
    STUDENT = "student"
    TOURIST = "tourist"
    WORK = "work"
    FAMILY = "family"
    INVESTOR = "investor"
    TRANSIT = "transit"


class EvidenceTier(str, Enum):
    """Evidence hierarchy enforced by the skill (highest -> lowest)."""
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"
    RCT_EMPIRICAL = "rct_empirical"
    COHORT = "cohort"
    EXPERT_OPINION = "expert_opinion"
    BLOG = "blog"
    NONE = "none"


TIER_WEIGHT = {
    EvidenceTier.SYSTEMATIC_REVIEW: 1.00,
    EvidenceTier.META_ANALYSIS: 0.95,
    EvidenceTier.RCT_EMPIRICAL: 0.85,
    EvidenceTier.COHORT: 0.70,
    EvidenceTier.EXPERT_OPINION: 0.45,
    EvidenceTier.BLOG: 0.20,
    EvidenceTier.NONE: 0.0,
}


class Effort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Impact(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# --------------------------------------------------------------------------- #
# Intake payload (output of sub-requirements-gatherer)
# --------------------------------------------------------------------------- #
REQUIRED_DOCUMENTS = {
    VisaClass.STUDENT: ["passport", "admission_letter", "financial_proof",
                        "academic_transcripts", "language_proof", "visa_application_form"],
    VisaClass.TOURIST: ["passport", "visa_application_form", "financial_proof",
                        "travel_itinerary", "ties_evidence", "accommodation_proof"],
    VisaClass.WORK: ["passport", "visa_application_form", "job_offer",
                     "employer_sponsorship", "qualification_proof", "financial_proof"],
    VisaClass.FAMILY: ["passport", "visa_application_form", "relationship_proof",
                       "sponsor_financial_proof", "accommodation_proof"],
    VisaClass.INVESTOR: ["passport", "visa_application_form", "investment_proof",
                         "business_plan", "source_of_funds"],
    VisaClass.TRANSIT: ["passport", "visa_application_form", "onward_ticket"],
}


@dataclass
class ApplicantIntake:
    nationality: str
    destination_country: str
    visa_class: VisaClass
    purpose: str
    travel_history: List[str] = field(default_factory=list)
    prior_refusals: List[str] = field(default_factory=list)
    prior_overstays: List[str] = field(default_factory=list)
    criminal_history: List[str] = field(default_factory=list)
    health_grounds: List[str] = field(default_factory=list)
    family_ties_home: List[str] = field(default_factory=list)
    employment_ties_home: List[str] = field(default_factory=list)
    financial_status: str = "unknown"            # stable | unstable | unknown
    documents_present: List[str] = field(default_factory=list)
    documents_missing: List[str] = field(default_factory=list)
    evidence_tier: EvidenceTier = EvidenceTier.NONE
    evidence_summary: str = ""
    assumptions: List[str] = field(default_factory=list)
    confidence: str = "medium"                    # low | medium | high

    def __post_init__(self):
        if not self.nationality or not isinstance(self.nationality, str):
            raise SchemaError("nationality is required (non-empty string)")
        if not self.destination_country or not isinstance(self.destination_country, str):
            raise SchemaError("destination_country is required (non-empty string)")
        if not self.purpose or not isinstance(self.purpose, str):
            raise SchemaError("purpose is required (non-empty string)")
        # Coerce string -> enum where callers pass raw JSON
        self.visa_class = VisaClass(self.visa_class) if not isinstance(self.visa_class, VisaClass) else self.visa_class
        self.evidence_tier = (EvidenceTier(self.evidence_tier)
                              if not isinstance(self.evidence_tier, EvidenceTier)
                              else self.evidence_tier)
        if self.confidence not in {"low", "medium", "high"}:
            raise SchemaError(f"confidence must be low|medium|high, got {self.confidence!r}")
        if self.financial_status not in {"stable", "unstable", "unknown"}:
            raise SchemaError(f"financial_status must be stable|unstable|unknown, got {self.financial_status!r}")
        # Derive missing documents if not supplied
        required = REQUIRED_DOCUMENTS.get(self.visa_class, [])
        present = {d.lower() for d in self.documents_present}
        if not self.documents_missing:
            self.documents_missing = [d for d in required if d.lower() not in present]

    def required_documents(self) -> List[str]:
        return REQUIRED_DOCUMENTS.get(self.visa_class, [])

    def to_dict(self) -> dict:
        d = asdict(self)
        d["visa_class"] = self.visa_class.value
        d["evidence_tier"] = self.evidence_tier.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ApplicantIntake":
        return cls(**data)


# --------------------------------------------------------------------------- #
# Compliance gate verdict (output of sub-compliance-check)
# --------------------------------------------------------------------------- #
@dataclass
class ComplianceVerdict:
    passed: bool
    blocking_conditions: List[str] = field(default_factory=list)
    requires_attorney: bool = False
    referral_note: str = ""
    admissibility_concerns: List[str] = field(default_factory=list)
    missing_mandatory_documents: List[str] = field(default_factory=list)
    framework_citations: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.passed, bool):
            raise SchemaError("ComplianceVerdict.passed must be bool")
        if self.requires_attorney and self.passed:
            # An attorney referral is itself a soft-block: harness may still
            # produce an informational report but MUST surface the referral.
            pass

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Scoring payload (output of sub-scoring-engine)
# --------------------------------------------------------------------------- #
DIMENSIONS = [
    "eligibility_fit",
    "document_completeness",
    "evidence_strength",
    "admissibility",
    "refusal_risk",
]
DEFAULT_WEIGHTS = {
    "eligibility_fit": 0.25,
    "document_completeness": 0.20,
    "evidence_strength": 0.20,
    "admissibility": 0.20,
    "refusal_risk": 0.15,
}


@dataclass
class DimensionScore:
    name: str
    score: float
    justification: str
    citations: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.name not in DIMENSIONS:
            raise SchemaError(f"unknown dimension {self.name!r}")
        if not (0 <= self.score <= 100):
            raise SchemaError(f"score for {self.name} must be 0-100, got {self.score}")
        if not self.justification or not isinstance(self.justification, str):
            raise SchemaError(f"justification required for {self.name}")
        if not self.citations:
            raise SchemaError(f"at least one citation required for {self.name}")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Scorecard:
    dimensions: List[DimensionScore] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    def __post_init__(self):
        names = [d.name for d in self.dimensions]
        for d in DIMENSIONS:
            if d not in names:
                raise SchemaError(f"scorecard missing dimension {d}")
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise SchemaError(f"weights must sum to 1.0, got {total}")

    @property
    def composite(self) -> float:
        return round(sum(d.score * self.weights[d.name] for d in self.dimensions), 1)

    def to_dict(self) -> dict:
        return {
            "composite": self.composite,
            "weights": self.weights,
            "dimensions": [d.to_dict() for d in self.dimensions],
        }


# --------------------------------------------------------------------------- #
# Roadmap payload (output of sub-improvement-roadmap)
# --------------------------------------------------------------------------- #
EFFORT_RANK = {Effort.LOW: 1, Effort.MEDIUM: 2, Effort.HIGH: 3}
IMPACT_RANK = {Impact.LOW: 1, Impact.MEDIUM: 2, Impact.HIGH: 3}


@dataclass
class RoadmapItem:
    action: str
    effort: Effort
    impact: Impact
    rationale: str
    owner: str = "applicant"
    expected_effect: str = ""
    citations: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.action or not isinstance(self.action, str):
            raise SchemaError("roadmap action required")
        self.effort = Effort(self.effort) if not isinstance(self.effort, Effort) else self.effort
        self.impact = Impact(self.impact) if not isinstance(self.impact, Impact) else self.impact
        if not self.rationale:
            raise SchemaError("roadmap rationale required")

    @property
    def priority(self) -> float:
        """Higher = more urgent. impact / effort."""
        return round(IMPACT_RANK[self.impact] / EFFORT_RANK[self.effort], 3)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["effort"] = self.effort.value
        d["impact"] = self.impact.value
        d["priority"] = self.priority
        return d


# --------------------------------------------------------------------------- #
# Final report
# --------------------------------------------------------------------------- #
@dataclass
class HarnessReport:
    subject: str
    purpose: str
    composite_score: float
    top_findings: List[str]
    scorecard: Scorecard
    roadmap: List[RoadmapItem]
    compliance_verdict: ComplianceVerdict
    assumptions: List[str]
    confidence: str
    limitations: List[str]
    sources: List[str]
    devils_advocate_notes: List[str]

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "purpose": self.purpose,
            "composite_score": self.composite_score,
            "top_findings": self.top_findings,
            "scorecard": self.scorecard.to_dict(),
            "roadmap": [r.to_dict() for r in self.roadmap],
            "compliance_verdict": self.compliance_verdict.to_dict(),
            "assumptions": self.assumptions,
            "confidence": self.confidence,
            "limitations": self.limitations,
            "sources": self.sources,
            "devils_advocate_notes": self.devils_advocate_notes,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def assert_quality_gates(report: HarnessReport) -> None:
    """Validate that a finished report satisfies all harness quality gates.

    Raises ``SchemaError`` if any gate is violated. Used by the test suite and
    by ``harness.run`` before emitting a final artifact.
    """
    cv = report.compliance_verdict
    # Gate 1: hard gate passed OR a referral/disclaimer issued
    if not cv.passed and not (cv.requires_attorney or cv.referral_note):
        raise SchemaError("hard gate failed and no referral/disclaimer issued")
    # Gate 2: every dimension cites a framework/source
    for d in report.scorecard.dimensions:
        if not d.citations:
            raise SchemaError(f"dimension {d.name} has no citation")
    # Gate 3: roadmap items carry effort + impact + rationale
    for r in report.roadmap:
        if not (r.effort and r.impact and r.rationale):
            raise SchemaError("roadmap item missing effort/impact/rationale")
    # Gate 4: assumptions, confidence, limitations stated
    if not report.assumptions or not report.confidence or not report.limitations:
        raise SchemaError("assumptions, confidence, and limitations are mandatory")
    # Gate 5: devil's-advocate pass completed
    if not report.devils_advocate_notes:
        raise SchemaError("devil's-advocate review not recorded")
