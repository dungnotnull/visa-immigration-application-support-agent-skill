# SECOND-KNOWLEDGE-BRAIN.md — Visa / Immigration Application Support

> Living, self-improving knowledge base for `visa-immigration-application-support`. Grown by `tools/knowledge_updater.py` from Crossref, Semantic Scholar, arXiv, and government RSS/Atom feeds. Run weekly (cron recommended).

## 1. Core Concepts & Frameworks
This skill reasons with the following world-renowned, citable frameworks:
- **Official eligibility criteria mapping (per visa class)**
- **Evidence sufficiency & document checklists**
- **Admissibility / inadmissibility grounds**
- **Genuine-intent & ties assessment**
- **Refusal-risk indicators & prior-refusal handling**
- **Procedural compliance (forms, fees, deadlines)**

Scoring dimensions derived from these: **Eligibility fit, Document completeness, Evidence strength, Admissibility, Refusal risk**.

## 2. Key Research Papers
| Title | Authors | Year | Venue | DOI/Link | Relevance |
|-------|---------|------|-------|----------|-----------|
| _(seed — populated by crawler on first live run)_ | — | — | Crossref / Semantic Scholar / arXiv | — | Structured API sources |
| _(seed — populated by crawler on first live run)_ | — | — | USCIS / UKVI / IRCC / Schengen official guidance | — | Authoritative policy sources |
| _(seed — populated by crawler on first live run)_ | — | — | Government visa policy bulletins | — | Authoritative policy sources |
| _(seed — populated by crawler on first live run)_ | — | — | AILA practice materials (general) | — | Practitioner commentary |
| _(seed — populated by crawler on first live run)_ | — | — | Migration Policy Institute reports | — | Empirical migration research |

## 3. State-of-the-Art Methods & Tools
- Current best practice is captured per-framework above; the crawler appends new methods as they appear.
- Evidence hierarchy enforced: Systematic Review > Meta-Analysis > RCT/empirical > Cohort > Expert Opinion > Blog.

## 4. Authoritative Data Sources
- USCIS / UKVI / IRCC / Schengen official guidance
- Government visa policy bulletins (RSS/Atom feeds)
- AILA practice materials (general)
- Migration Policy Institute reports
- Crossref, Semantic Scholar, arXiv (structured research APIs)

## 5. Analytical Frameworks (used for evaluation)
- **Official eligibility criteria mapping (per visa class)**
- **Evidence sufficiency & document checklists**
- **Admissibility / inadmissibility grounds**
- **Genuine-intent & ties assessment**
- **Refusal-risk indicators & prior-refusal handling**
- **Procedural compliance (forms, fees, deadlines)**

## 6. Self-Update Protocol (knowledge_updater.py)
- **Sources:** Crossref REST API, Semantic Scholar Graph API, arXiv API, USCIS/UKVI/IRCC RSS/Atom feeds.
- **Search queries:** visa refusal reasons statistics, document checklist visa class update, immigration policy change announcement, genuine intent assessment criteria.
- **Frequency:** weekly (cron).
- **Append format:** dated entry -> Title | Authors | Year | Venue | URL | score | `<!--hash:...-->`.
- **Dedup:** URL/title SHA-256 hash check before append.
- **Filtering:** `--since YYYY-MM-DD` keeps entries from that year onward; relevance score = 0.5*recency + 0.5*keyword-relevance.

## 7. Knowledge Update Log
- 2026-07-06 — Knowledge base rebuilt for production: frameworks registered, structured-API crawler (`tools/knowledge_updater.py`) ready for first live run, deterministic harness and tests in place. Awaiting first scheduled crawl.
