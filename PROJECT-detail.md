# PROJECT-detail.md — Visa / Immigration Application Support

## Executive Summary
`visa-immigration-application-support` is a Claude Skill that turns Claude into **an immigration-application analyst who checks completeness, eligibility, and evidence strength against official requirements (informational, not legal advice)**. It ingests domain inputs, screens for safety/compliance where required, selects a world-renowned evaluation framework, gathers fresh evidence, scores the subject across 5 dimensions, and outputs a prioritized improvement roadmap. It is part of the **Legal, Compliance & Governance** cluster.

## Problem Statement
Applicants face complex, high-stakes visa/immigration forms where small omissions cause refusals; they need a rigorous completeness/eligibility/evidence review with clear non-lawyer framing.

Domain context: practitioners need reproducible, evidence-graded evaluation rather than ad-hoc opinion. This skill enforces a research-first harness with explicit quality gates and a self-improving knowledge base.

## Target Users & Use Cases
- Primary: practitioners, learners, and decision-makers in this domain.
- Trigger examples:
1. **Student visa evidence** — Applicant unsure of financial proof. Expect checklist, evidence-strength scoring, compliance disclaimer.
2. **Prior refusal handling** — Earlier refusal exists. Expect compliance-check flag and a strengthening roadmap, plus 'see an attorney' note.
3. **Inadmissibility concern** — Past visa overstay. Expect admissibility analysis and explicit attorney-referral gate.
4. **Tourist visa ties** — Weak home-country ties. Expect genuine-intent strengthening roadmap.
5. **Work visa eligibility** — Job offer + qualifications. Expect eligibility-fit scoring against the visa class criteria.

## Harness Architecture
```
/visa-immigration-application-support  (main.md)
   │
   →
[1] sub-requirements-gatherer        → structured intake
   │
   →
[2] GATE: sub-compliance-check  → blocks unsafe/non-compliant requests
   │
   →
[3] research (WebSearch/WebFetch)        → evidence (graceful deg: SECOND-KNOWLEDGE-BRAIN.md)
   │
   →
[4] scoring engine                       → 0-100 multi-dimensional score
   │
   →
[5] improvement roadmap                  → effort x impact prioritized actions
   │
   →
[6] quality-gate / devil's advocate      → final professional artifact
```

## Full Sub-Skill Catalog
#### `sub-requirements-gatherer`
- **Purpose:** Capture nationality, visa class, destination country, purpose, and history.
- **Inputs:** structured outputs from prior stage + user-supplied data
- **Outputs:** validated, structured payload for the next stage
- **Tools:** Read, Write
- **Quality gate:** output schema validated before proceeding

#### `sub-compliance-check`
- **Purpose:** Verify eligibility, admissibility, and required-document completeness against official rules before any output; flag where a licensed attorney is required.
- **Inputs:** structured outputs from prior stage + user-supplied data
- **Outputs:** validated, structured payload for the next stage
- **Tools:** Read, Write
- **Quality gate:** BLOCKS the harness until satisfied (hard gate)

#### `sub-scoring-engine`
- **Purpose:** Score completeness, eligibility fit, evidence strength, admissibility, and refusal risk.
- **Inputs:** structured outputs from prior stage + user-supplied data
- **Outputs:** validated, structured payload for the next stage
- **Tools:** Read, Write, WebSearch/WebFetch
- **Quality gate:** output schema validated before proceeding

#### `sub-improvement-roadmap`
- **Purpose:** Recommend documents, evidence, and statements to strengthen, ranked by refusal-risk reduction.
- **Inputs:** structured outputs from prior stage + user-supplied data
- **Outputs:** validated, structured payload for the next stage
- **Tools:** Read, Write
- **Quality gate:** output schema validated before proceeding


## Evaluation Frameworks (world-renowned, citable)
- Official eligibility criteria mapping (per visa class)
- Evidence sufficiency & document checklists
- Admissibility / inadmissibility grounds
- Genuine-intent & ties assessment
- Refusal-risk indicators & prior-refusal handling
- Procedural compliance (forms, fees, deadlines)

## Scoring Model
| Dimension | Range | Notes |
|-----------|-------|-------|
| Eligibility fit | 0–100 | Weighted contribution to the composite index |
| Document completeness | 0–100 | Weighted contribution to the composite index |
| Evidence strength | 0–100 | Weighted contribution to the composite index |
| Admissibility | 0–100 | Weighted contribution to the composite index |
| Refusal risk | 0–100 | Weighted contribution to the composite index (higher = safer) |

Composite = weighted mean of dimensions (weights justified per case, surfaced to the user). Every dimension score must cite at least one framework criterion or evidence source.

## Skill File Format Specification
Frontmatter: `name`, `description`. Required sections in `main.md`: Role & Persona, Workflow (Harness Flow), Sub-skills Available, Tools, Output Format, Quality Gates.

## E2E Execution Flow
1. Parse user request; if inputs missing, run intake questions.
2. Run hard gate; if it fails, STOP and emit referral/disclaimer.
3. Gather evidence (prefer Systematic Review > Meta-analysis > RCT/empirical > expert opinion).
4. Score each dimension with cited justification.
5. Build prioritized roadmap.
6. Run devil's-advocate quality gate; revise; present artifact.
- Error handling: missing data → state assumptions + confidence; tool failure → degrade to knowledge base and signal limitation.

## SECOND-KNOWLEDGE-BRAIN Integration
- Sources: USCIS / UKVI / IRCC / Schengen official guidance, Government visa policy bulletins, AILA practice materials (general), Migration policy institute reports.
- Crawl queries: visa refusal reasons statistics, document checklist visa class update, immigration policy change announcement, genuine intent assessment criteria.
- Append format: dated entries with Title, Authors, Year, Venue, DOI/URL, key finding, relevance.

## Supporting Tools Spec — `knowledge_updater.py`
- Inputs: source list + query list (above), `--since` date.
- Outputs: appended, de-duplicated entries in `SECOND-KNOWLEDGE-BRAIN.md`.
- Schedule: weekly cron.
- Implementation: structured APIs (Crossref, Semantic Scholar, arXiv) + government RSS/Atom feeds; SHA-256 dedup; stdlib-only.

## Quality Gates (must be true before final output)
- [ ] Hard safety/risk/compliance gate passed or referral issued
- [ ] Every score cites a framework criterion or evidence source
- [ ] Roadmap items have effort + impact + owner
- [ ] Assumptions and confidence stated; limitations disclosed
- [ ] Devil's-advocate pass completed

## Test Scenarios (>=5)
1. **Student visa evidence** — Applicant unsure of financial proof. Expect checklist, evidence-strength scoring, compliance disclaimer.
2. **Prior refusal handling** — Earlier refusal exists. Expect compliance-check flag and a strengthening roadmap, plus 'see an attorney' note.
3. **Inadmissibility concern** — Past visa overstay. Expect admissibility analysis and explicit attorney-referral gate.
4. **Tourist visa ties** — Weak home-country ties. Expect genuine-intent strengthening roadmap.
5. **Work visa eligibility** — Job offer + qualifications. Expect eligibility-fit scoring against the visa class criteria.

## Key Design Decisions
1. Research-first; no memory-only claims when search is possible.
2. Named frameworks only — never ad hoc criteria.
3. Hard gate precedes all guidance for this safety/compliance-sensitive domain.
4. Multi-dimensional score + prioritized roadmap are mandatory outputs.
5. Self-improving knowledge base via weekly crawl.
6. Deterministic reference implementation (tools/schema.py, tools/harness.py) so the harness is runnable and testable without an LLM.
