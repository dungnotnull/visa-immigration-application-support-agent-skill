# CLAUDE.md — Visa / Immigration Application Support (idea 126)

## Skill Identity
- **Name / slug:** `visa-immigration-application-support`
- **Tagline:** Visa / Immigration Application Support
- **Source idea:** #126 (`ideas.md`)
- **Cluster:** Legal, Compliance & Governance (`legal-compliance`)
- **Current phase:** Phase 5 — Integration & Cross-Skill Wiring (complete)

## Problem This Skill Solves
Applicants face complex, high-stakes visa/immigration forms where small omissions cause refusals; they need a rigorous completeness/eligibility/evidence review with clear non-lawyer framing.

This skill becomes **an immigration-application analyst who checks completeness, eligibility, and evidence strength against official requirements (informational, not legal advice)**. It is research-first, grounds every score in named world-renowned frameworks, challenges its own assumptions before concluding, and produces a professional artifact: a multi-dimensional score plus a prioritized improvement roadmap.

## Harness Flow Summary
1. **Intake** -> `sub-requirements-gatherer` gathers structured inputs into a schema-valid `ApplicantIntake`.
2. **Gate / framework** -> `sub-compliance-check` HARD GATE runs; on block, STOP and emit attorney referral.
3. **Research** -> WebSearch/WebFetch enrich evidence from authoritative sources (graceful degradation to `SECOND-KNOWLEDGE-BRAIN.md` if unavailable).
4. **Scoring** -> `sub-scoring-engine` produces a 0-100 multi-dimensional score + weighted composite.
5. **Roadmap** -> prioritized improvement plan (effort x impact).
6. **Quality gate** -> devil's-advocate review + `assert_quality_gates` before final output.

**COMPLIANCE GATE:** `sub-compliance-check` MUST pass before the final deliverable; flags where a licensed professional is required.

## Sub-skills
- `skills/sub-requirements-gatherer.md` — Capture nationality, visa class, destination country, purpose, and history into a schema-valid payload.
- `skills/sub-compliance-check.md` — HARD GATE: verify eligibility, admissibility, and required-document completeness; flag where a licensed attorney is required.
- `skills/sub-scoring-engine.md` — Score the five dimensions and compute the weighted composite.
- `skills/sub-improvement-roadmap.md` — Recommend documents, evidence, and statements to strengthen, ranked by refusal-risk reduction.

## Reference Implementation (deterministic, no LLM required)
- `tools/schema.py` — typed payloads + `assert_quality_gates`.
- `tools/harness.py` — `run()` orchestration + `render_markdown()` + CLI (`python tools/harness.py --input <file> --output report.md`).
- `tools/knowledge_updater.py` — Crossref / Semantic Scholar / arXiv / RSS crawler for `SECOND-KNOWLEDGE-BRAIN.md`.
- `tests/test_harness.py` — 27 deterministic regression tests (run with `pytest`).

## Tools Required
- `WebSearch`, `WebFetch` — live evidence gathering (graceful degradation to knowledge base)
- `Read`, `Write` — artifact production
- `Bash`/`python` — run `tools/harness.py` and `tools/knowledge_updater.py`

## Knowledge Sources (crawl targets)
- USCIS / UKVI / IRCC / Schengen official guidance (RSS/Atom)
- Crossref, Semantic Scholar, arXiv (structured research APIs)
- Government visa policy bulletins
- AILA practice materials (general)
- Migration Policy Institute reports

## Supporting Tools
- `tools/knowledge_updater.py` — structured-API pipeline that grows `SECOND-KNOWLEDGE-BRAIN.md` (weekly cron recommended).
- `tools/harness.py` + `tools/schema.py` — deterministic reference implementation of the harness.

## Active Development Tasks
- [x] Scaffold all required deliverables
- [x] Author main harness + 4 sub-skills (concrete schemas, frameworks, rubrics)
- [x] Define scoring dimensions: Eligibility fit, Document completeness, Evidence strength, Admissibility, Refusal risk
- [x] Build deterministic reference implementation (`tools/schema.py`, `tools/harness.py`)
- [x] Production-grade knowledge updater (structured APIs, dedup, CLI)
- [x] 6 regression scenarios + 27 automated tests (pytest, all passing)
- [x] Cross-skill wiring (`CROSS-SKILL-WIRING.md`)
- [ ] First scheduled live crawl (cron, not run during build to save resources)

## Related Root Docs
- `PROJECT-detail.md` — full technical spec
- `PROJECT-DEVELOPMENT-PHASE-TRACKING.md` — phase roadmap
- `SECOND-KNOWLEDGE-BRAIN.md` — living knowledge base
- `CROSS-SKILL-WIRING.md` — cluster integration
