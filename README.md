# Visa & Immigration Application Support — Agent Skill

> A Claude / agent skill that turns an LLM into a rigorous **immigration-application analyst**: it screens an application through a hard compliance gate, scores it 0–100 across five framework-grounded dimensions, and outputs a prioritized improvement roadmap. **Informational only — never legal advice.**

[![Tests](https://img.shields.io/badge/tests-27%2F27%20passing-brightgreen)](#testing)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](#requirements)
[![License](https://img.shields.io/badge/license-MIT-green)](#license)
[![Phase](https://img.shields.io/badge/status-production%20ready-brightgreen)](#project-status)

---

## Table of Contents
1. [What this skill does](#what-this-skill-does)
2. [Why it exists](#why-it-exists)
3. [Architecture at a glance](#architecture-at-a-glance)
4. [The harness flow](#the-harness-flow)
5. [Scoring model](#scoring-model)
6. [The hard compliance gate](#the-hard-compliance-gate)
7. [Repository layout](#repository-layout)
8. [Quick start](#quick-start)
9. [The reference implementation (no LLM needed)](#the-reference-implementation-no-llm-needed)
10. [Knowledge base updater](#knowledge-base-updater)
11. [Testing](#testing)
12. [Sample output](#sample-output)
13. [Cross-skill wiring](#cross-skill-wiring)
14. [Configuration & extension](#configuration--extension)
15. [Limitations & disclaimers](#limitations--disclaimers)
16. [Project status](#project-status)
17. [License](#license)

---

## What this skill does

`visa-immigration-application-support` is an **agent skill** (a structured instruction set plus a deterministic reference runtime) that analyzes a visa or immigration application and produces a professional, evidence-graded assessment artifact. Given an applicant profile it will:

1. **Validate intake** — nationality, destination, visa class, purpose, documents, ties, history.
2. **Run a HARD compliance gate** — block and issue an attorney referral if admissibility or refusal-risk red flags are present.
3. **Score five dimensions** 0–100 — Eligibility fit, Document completeness, Evidence strength, Admissibility, Refusal risk — each with a cited justification.
4. **Compute a weighted composite** and surface the weights used.
5. **Build a prioritized improvement roadmap** — actions ranked by `impact / effort`.
6. **Run a devil's-advocate quality gate** before emitting the final Markdown report.

Every judgment is grounded in a **named, citable framework**. Nothing is invented; when live evidence is unavailable the harness degrades gracefully to the local knowledge base and says so explicitly.

## Why it exists

Visa and immigration forms are high-stakes: a small omission or an unaddressed refusal history can cause a refusal that costs months and money. Applicants (and the practitioners helping them) need a reproducible, evidence-graded review rather than ad-hoc opinion — while staying clearly within **informational, non-legal** territory. This skill enforces a research-first harness with explicit quality gates and a self-improving knowledge base.

**Cluster:** Legal, Compliance & Governance (`legal-compliance`).

## Architecture at a glance

```
User request
   │
   →
[1] sub-requirements-gatherer   →  schema-valid ApplicantIntake
   │
   →
[2] sub-compliance-check (HARD GATE)  →  ComplianceVerdict (pass / BLOCK + referral)
   │  (if blocked → STOP, emit referral, skip scoring)
   →
[3] evidence gathering          →  WebSearch/WebFetch, or SECOND-KNOWLEDGE-BRAIN.md
   │
   →
[4] sub-scoring-engine          →  Scorecard (5 dimensions + composite)
   │
   →
[5] sub-improvement-roadmap     →  prioritized RoadmapItem list
   │
   →
[6] devil's-advocate + assert_quality_gates  →  final Markdown artifact
```

The **LLM-driven steps** (free-text intake, live web evidence, narrative devil's-advocate) plug in around a **deterministic core** (`tools/schema.py` + `tools/harness.py`) so the whole harness can be executed and regression-tested without an LLM.

## The harness flow

1. **Intake** — `sub-requirements-gatherer` gathers all required inputs into a schema-valid `ApplicantIntake`. Missing essentials trigger targeted questions (batched, up to 4) before proceeding.
2. **HARD GATE** — `sub-compliance-check` runs before anything substantive. If it trips, the harness **stops**: it emits the attorney referral/disclaimer and the single referral roadmap item, and does **not** produce scores or a full plan.
3. **Evidence gathering** — `WebSearch`/`WebFetch` against authoritative sources (USCIS / UKVI / IRCC / Schengen official guidance, government policy bulletins, AILA practice materials, Migration Policy Institute). Prefer the highest evidence tier. If tools are unavailable, fall back to `SECOND-KNOWLEDGE-BRAIN.md` and state the limitation.
4. **Scoring** — `sub-scoring-engine` scores the five dimensions 0–100, each with a cited justification, then computes the weighted composite.
5. **Roadmap** — `sub-improvement-roadmap` produces actions ranked by refusal-risk reduction (`impact / effort`), each carrying effort, impact, rationale, owner, and expected effect.
6. **Quality gate** — a devil's-advocate review challenges the scores and recommendations; `assert_quality_gates` enforces the five mandatory gates before the artifact is emitted.

## Scoring model

| Dimension | Default weight | Direction | Framework |
|-----------|----------------|-----------|-----------|
| Eligibility fit | 0.25 | higher = better | Official eligibility criteria mapping (per visa class) |
| Document completeness | 0.20 | higher = better | Evidence sufficiency & document checklists |
| Evidence strength | 0.20 | higher = better | Evidence sufficiency & document checklists |
| Admissibility | 0.20 | higher = better | Admissibility / inadmissibility grounds |
| Refusal risk | 0.15 | higher = safer | Refusal-risk indicators & prior-refusal handling |

- **Composite** = weighted mean of the five dimensions, rounded to 1 decimal.
- Weights **must** sum to 1.0 and are surfaced to the user. They may be re-justified per case (e.g. raise the admissibility weight when admissibility is the live issue), but any change and its rationale must be stated.
- **Every dimension score must cite at least one framework criterion or evidence source** — a dimension with no citation fails the quality gate.

### Evidence tier hierarchy (highest → lowest)

| Tier | Weight | Example |
|------|--------|---------|
| `systematic_review` | 1.00 | Systematic reviews of migration decisions |
| `meta_analysis` | 0.95 | Meta-analyses of refusal-rate predictors |
| `rct_empirical` | 0.85 | Government empirical evaluations, RCT-style pilots |
| `cohort` | 0.70 | Cohort studies of visa outcomes |
| `expert_opinion` | 0.45 | AILA practice materials, official-guidance commentary |
| `blog` | 0.20 | Non-authoritative blog posts (weak) |
| `none` | 0.00 | No evidence supplied |

## The hard compliance gate

The gate is **blocking and cannot be bypassed**. Any one of these trips it (BLOCK + attorney referral):

1. **Prior overstay** recorded in any country.
2. **Serious criminal history** — moral turpitude, controlled substance, trafficking, firearms, or violent offenses.
3. **Health grounds** of public-health concern.
4. **Prior refusal for the same visa class AND destination**.
5. **No mandatory documents present at all** (assessment impossible).

When blocked, the harness emits the standard referral:

> This assessment is informational and not legal advice. The indicators above require review by a licensed immigration attorney before filing.

…and produces only the single roadmap item "Resolve blocking conditions / consult a licensed immigration attorney", skipping substantive scoring/roadmap work.

### Required-document checklist (canonical, per visa class)

| Visa class | Required documents |
|------------|--------------------|
| `student` | passport, admission_letter, financial_proof, academic_transcripts, language_proof, visa_application_form |
| `tourist` | passport, visa_application_form, financial_proof, travel_itinerary, ties_evidence, accommodation_proof |
| `work` | passport, visa_application_form, job_offer, employer_sponsorship, qualification_proof, financial_proof |
| `family` | passport, visa_application_form, relationship_proof, sponsor_financial_proof, accommodation_proof |
| `investor` | passport, visa_application_form, investment_proof, business_plan, source_of_funds |
| `transit` | passport, visa_application_form, onward_ticket |

## Repository layout

```
visa-immigration-application-support/
┌── skills/                              # The agent-skill instruction set (Markdown)
│   • main.md                          #   Main harness: persona, flow, gates, output format
│   • sub-requirements-gatherer.md     #   Intake stage + schema
│   • sub-compliance-check.md          #   HARD GATE + blocking conditions + checklist
│   • sub-scoring-engine.md            #   Scoring rubrics + weights
│   ├── sub-improvement-roadmap.md       #   Prioritization model + item templates
┌── tools/                              # Deterministic reference runtime
│   • schema.py                        #   Typed payloads + assert_quality_gates
│   • harness.py                       #   run() orchestration + render_markdown() + CLI
│   ├── knowledge_updater.py             #   Structured-API crawler for the knowledge base
┌── tests/
│   • test-scenarios.md                #   6 scenarios + expected behavior + checklist
│   • test_harness.py                  #   27 automated pytest tests
│   ├── fixtures/                        #   6 JSON intake fixtures
┌── CLAUDE.md                            # Skill identity + harness summary
• CROSS-SKILL-WIRING.md                # Cluster sharing + scoring-scale alignment
• PROJECT-detail.md                    # Full technical spec
• PROJECT-DEVELOPMENT-PHASE-TRACKING.md# Phase roadmap (all phases DONE)
• SECOND-KNOWLEDGE-BRAIN.md           # Living, self-improving knowledge base
├── README.md                            # This file
```

## Quick start

### Requirements
- Python **3.8+** (stdlib only for the harness and tests).
- `pytest` for the test suite (`pip install pytest`).
- The knowledge updater is also stdlib-only (uses `urllib`); no `requests` or `crawl4ai` required.

### Run an assessment

```bash
# From the repo root — analyze a sample applicant and write a Markdown report
python tools/harness.py --input tests/fixtures/student_visa.json --output report.md

# Or print to stdout as Markdown
python tools/harness.py --input tests/fixtures/work_visa.json

# Or emit JSON
python tools/harness.py --input tests/fixtures/tourist_weak_ties.json --json
```

### Run the tests

```bash
pip install pytest
pytest tests/test_harness.py -q
```

Expected: **27 passed**.

## The reference implementation (no LLM needed)

The deterministic core lets you run, validate, and regression-test the harness without invoking any model.

- **`tools/schema.py`** — dataclasses (`ApplicantIntake`, `ComplianceVerdict`, `DimensionScore`, `Scorecard`, `RoadmapItem`, `HarnessReport`) that validate on construction via `__post_init__`, plus `assert_quality_gates()` which enforces the five mandatory harness gates.
- **`tools/harness.py`** — `run(data, evidence_fn=None, devil_fn=None)` orchestrates intake → gate → evidence → scoring → roadmap → devil's-advocate → quality-gate. `render_markdown(report)` produces the artifact. The CLI wraps it all.

LLM-driven steps plug in via optional callbacks:

```python
import sys; sys.path.insert(0, "tools")
from harness import run, render_markdown

def live_evidence(intake):
    # call WebSearch / WebFetch here and return a list of dicts:
    # [{"title": ..., "url": ..., "tier": "cohort"}, ...]
    return []

def devils_advocate(report):
    # return a list of critique strings
    return ["Challenged the weakest dimension; confirmed citations."]

report = run(intake_dict, evidence_fn=live_evidence, devil_fn=devils_advocate)
print(render_markdown(report))
```

When `evidence_fn` is absent or raises, the harness degrades gracefully to `SECOND-KNOWLEDGE-BRAIN.md` and records the limitation in the report.

## Knowledge base updater

`tools/knowledge_updater.py` grows `SECOND-KNOWLEDGE-BRAIN.md` from **authoritative structured sources** (no Google scraping, no browser automation, no heavy ML deps):

- **Crossref REST API** — official DOI metadata.
- **Semantic Scholar Graph API** — peer-reviewed migration research.
- **arXiv API** — quantitative migration / policy preprints.
- **Government RSS/Atom feeds** — live USCIS / UKVI / IRCC policy bulletins.

Each candidate is scored (`0.5 * recency + 0.5 * keyword-relevance`) and de-duplicated by a SHA-256 hash of its URL/title before being appended as a dated entry.

```bash
# Dry run — print candidates as JSON, write nothing
python tools/knowledge_updater.py --dry-run --limit 5

# Live append to the knowledge base
python tools/knowledge_updater.py --since 2024-01-01 --limit 10

# Restrict to specific sources
python tools/knowledge_updater.py --sources crossref,arxiv

# Point at a different knowledge file
python tools/knowledge_updater.py --brain /path/to/SECOND-KNOWLEDGE-BRAIN.md
```

Schedule it weekly via cron for a self-improving knowledge base.

## Testing

The suite is deterministic and requires **no network and no LLM**.

```bash
pytest tests/test_harness.py -v
```

Coverage:

- **Schema validation** — required fields, enum normalization, derived missing docs, invalid confidence, citation requirement, weight sum, priority computation.
- **Scoring rubrics** — eligibility full/partial credit, completeness ratio, evidence tier weight, refusal-risk factors, admissibility penalties.
- **Hard gate** — blocks on overstay, serious crime, same-class/destination refusal, no-documents; passes a clean case.
- **End-to-end scenarios** — all 6 fixtures, each asserting the correct gate decision, roadmap shape, and quality-gate compliance.
- **Roadmap** — sorted by priority descending, de-duplicated by action.
- **Graceful degradation** — limitation recorded when no live evidence; live callback path verified.
- **Rendering & CLI** — all 7 report sections present; CLI writes a valid report file.

### Test scenarios

| # | Fixture | Expected gate | Highlights |
|---|---------|---------------|------------|
| 1 | `student_visa.json` | PASS | 5/6 docs; roadmap flags missing form + evidence upgrade |
| 2 | `prior_refusal.json` | BLOCK | same-class/destination refusal → attorney referral |
| 3 | `inadmissibility_overstay.json` | BLOCK | prior overstay → admissibility concern + referral |
| 4 | `tourist_weak_ties.json` | PASS | weak ties lower refusal-risk score; ties roadmap item |
| 5 | `work_visa.json` | PASS | full docs, high evidence tier; minimal roadmap |
| 6 | `blocked_no_docs.json` | BLOCK | no mandatory docs → referral only |

## Sample output

Running `python tools/harness.py --input tests/fixtures/work_visa.json` produces:

```markdown
# Visa / Immigration Application Support - Assessment Report

> Informational analysis only. This is NOT legal advice.

## 1. Summary
- **Subject:** Nigeria applicant -> Canada (work)
- **Purpose:** work - software engineer role
- **Composite score:** 97.0/100
- **Top findings:**
  - Composite score 97.0/100
  - evidence_strength = 85.0: Evidence tier: rct_empirical (weight 0.85).
  - eligibility_fit = 100.0: 3/3 core eligibility criteria met for work visa; purpose alignment yes.

## 2. Compliance Gate Verdict
- **Passed:** True
- **Requires attorney:** False

## 3. Scorecard
| Dimension | Score | Justification | Citations |
|-----------|-------|---------------|-----------|
| eligibility_fit | 100.0 | 3/3 core eligibility criteria met ... | Official eligibility criteria mapping ... |
...
```

## Cross-skill wiring

This skill is the **source of truth** for shared components in the `legal-compliance` cluster. Sibling skills reuse:

- `tools/schema.py` — canonical typed payloads (import, or vendor-and-pin a commit).
- The hard-gate pattern (`ComplianceVerdict` shape + STOP behavior).
- `assert_quality_gates()` — the five mandatory quality gates.
- `tools/knowledge_updater.py` — point `--brain` at the sibling's knowledge file and override keywords.
- `EvidenceTier` + `TIER_WEIGHT` — the shared evidence hierarchy.

All siblings adopt the same scoring conventions: **0–100 per dimension, weighted-mean composite, higher = better/safer, mandatory citation per dimension.** See [`CROSS-SKILL-WIRING.md`](CROSS-SKILL-WIRING.md) for the full divergence-prevention contract.

## Configuration & extension

- **Add a visa class** — extend `VisaClass` in `tools/schema.py`, add its required docs to `REQUIRED_DOCUMENTS`, and its core criteria to `ELIGIBILITY_CRITERIA` in `tools/harness.py`.
- **Re-weight a case** — pass custom `weights` to `run_scoring` (must sum to 1.0); surface them in the output.
- **Add a knowledge source** — add an adapter function to `tools/knowledge_updater.py` and register it in `ADAPTERS`.
- **Plug in live search** — pass an `evidence_fn` callback to `harness.run`.

## Limitations & disclaimers

- **This is informational analysis, not legal advice.** It does not create an attorney-client relationship. Where the gate refers you to a licensed immigration attorney, consult one before filing.
- The deterministic rubric is a transparent, reproducible heuristic — not a prediction of any government's decision.
- Scoring reflects the inputs supplied; incomplete intake yields lower confidence and stated assumptions.
- When live web search is unavailable, evidence is drawn from the local knowledge base and the limitation is disclosed in the report.

## Project status

All development phases are **complete**:

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Research & skill architecture | DONE |
| 1 | Core sub-skills | DONE |
| 2 | Main harness + quality gates | DONE |
| 3 | SECOND-KNOWLEDGE-BRAIN pipeline | DONE |
| 4 | Testing & validation | DONE |
| 5 | Integration & cross-skill wiring | DONE |

See [`PROJECT-DEVELOPMENT-PHASE-TRACKING.md`](PROJECT-DEVELOPMENT-PHASE-TRACKING.md) for the full roadmap.

## License

Released under the **MIT License**. See the repository for details.

> Built as an open-source agent skill. Contributions welcome — please ensure `pytest tests/test_harness.py` stays green and that every score continues to cite a framework or evidence source.
