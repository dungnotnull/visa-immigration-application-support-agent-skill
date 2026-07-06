# CROSS-SKILL-WIRING.md — Visa / Immigration Application Support

Phase 5 deliverable: integration & cross-skill wiring. This document defines how the cluster sub-skills of the **Legal, Compliance & Governance** cluster are shared with sibling skills without divergence, and how scoring scales are aligned across the cluster.

## Cluster
`legal-compliance` (Legal, Compliance & Governance)

## Sibling Skills (shareable components)
Sibling skills in this cluster reuse the following components from `visa-immigration-application-support`:

| Component | Path | Shared as | How to reuse |
|-----------|------|-----------|--------------|
| Shared schemas | `tools/schema.py` | Canonical typed payloads (`ApplicantIntake`, `ComplianceVerdict`, `Scorecard`, `RoadmapItem`, `HarnessReport`) | Import from this skill's `tools/` via a relative path, or vendor a copy and pin a version. Never edit the schema in a sibling without updating this source of truth. |
| Hard-gate pattern | `skills/sub-compliance-check.md` + `harness.run_compliance_gate` | The "evaluate blockers -> BLOCK + attorney referral" contract | Siblings implement their own blocking-condition list but MUST keep the same `ComplianceVerdict` shape and STOP behavior. |
| Quality-gate contract | `schema.assert_quality_gates` | The 5 harness quality gates (gate/referral, citations, roadmap completeness, assumptions, devil's-advocate) | Siblings call `assert_quality_gates` before emitting a final artifact. |
| Knowledge updater | `tools/knowledge_updater.py` | Crossref / Semantic Scholar / arXiv / RSS pipeline with dedup + scoring | Reuse by pointing `--brain` at the sibling's knowledge file and overriding `DOMAIN_KEYWORDS`. |
| Evidence tier hierarchy | `schema.EvidenceTier` + `TIER_WEIGHT` | Systematic Review > Meta-analysis > RCT/empirical > Cohort > Expert opinion > Blog | Sibling scorers MUST use the same tier weights so scores are comparable. |

## Scoring-Scale Alignment
To keep scores comparable across the cluster, all sibling skills adopt:
- A **0-100** scale per dimension.
- A **weighted-mean composite** with weights summing to 1.0, surfaced to the user.
- The same **direction convention**: higher = better/safer (including risk dimensions, which are expressed as a "safety score" = 100 - risk).
- The same **citation rule**: every dimension score cites at least one framework or evidence source.

`visa-immigration-application-support`'s default weights:
```
eligibility_fit=0.25, document_completeness=0.20, evidence_strength=0.20,
admissibility=0.20, refusal_risk=0.15
```
Sibling skills MAY define different dimensions and weights, but they MUST publish them and keep the 0-100 + weighted-mean + higher-is-better conventions.

## Divergence Prevention
1. **Single source of truth for schemas:** `tools/schema.py`. Sibling skills import or vendor-and-pin (record the pinned commit).
2. **No silent edits:** any change to `ComplianceVerdict`, `Scorecard`, `RoadmapItem`, or `assert_quality_gates` is a cluster-wide breaking change and must be reflected in siblings.
3. **Aligned evidence tiers:** `EvidenceTier` + `TIER_WEIGHT` are shared; do not invent per-skill tiers.
4. **Regression contract:** siblings reuse the deterministic test pattern (`tests/test_harness.py`) so gate/scoring behavior stays reproducible.

## Cross-Skill References (registry)
| Skill | Shared components used | Notes |
|-------|------------------------|-------|
| `visa-immigration-application-support` (this) | origin of schema, gate pattern, quality gates, knowledge updater, evidence tiers | Source of truth. |
| `*` (future legal-compliance siblings) | import `tools/schema.py`; reuse `ComplianceVerdict` + `assert_quality_gates`; reuse `knowledge_updater.py` with own keywords + `--brain` | Align dimensions/weights to the 0-100 weighted-mean convention above. |

## Success Criteria (Phase 5)
- [x] Shared sub-skills (Legal, Compliance & Governance) documented for sibling reuse
- [x] Scoring scales aligned (0-100, weighted mean, higher-is-better, citation rule)
- [x] Single source of truth for schemas (`tools/schema.py`)
- [x] Cross-skill references published in this file
- [x] Shared sub-skills reusable without divergence (import / vendor-and-pin contract defined)
