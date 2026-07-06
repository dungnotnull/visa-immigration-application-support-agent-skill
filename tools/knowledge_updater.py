"""
knowledge_updater.py - SECOND-KNOWLEDGE-BRAIN crawler for
``visa-immigration-application-support`` (idea 126).

Production-grade, dependency-light pipeline that grows
``SECOND-KNOWLEDGE-BRAIN.md`` with dated, de-duplicated, relevance-scored
entries from authoritative structured sources:

  1. Crossref REST API        - official DOI metadata (government & policy docs)
  2. Semantic Scholar Graph API - peer-reviewed migration research
  3. arXiv API                - quantitative migration / policy preprints
  4. Government RSS/Atom feeds - live policy bulletins (USCIS / UKVI / IRCC)

No Google scraping, no browser automation, no heavy ML deps. The pipeline is
pure-stdlib + optional ``requests`` (falls back to ``urllib`` if absent), so it
runs in any production environment / weekly cron with zero exotic installs.

Outputs: appends a dated, hash-de-duplicated block to SECOND-KNOWLEDGE-BRAIN.md.

CLI:
    python tools/knowledge_updater.py                       # live append
    python tools/knowledge_updater.py --dry-run            # print candidates only
    python tools/knowledge_updater.py --since 2025-01-01   # only entries after date
    python tools/knowledge_updater.py --limit 20           # cap per source
    python tools/knowledge_updater.py --sources crossref,arxiv
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.normpath(os.path.join(HERE, "..", "SECOND-KNOWLEDGE-BRAIN.md"))

USER_AGENT = "visa-immigration-knowledge-updater/1.0 (+open-source skill; contact: repo maintainer)"

DOMAIN_KEYWORDS = [
    "visa refusal", "visa refusal reasons", "visa refusal statistics",
    "document checklist", "visa class", "immigration policy",
    "policy change announcement", "genuine intent", "genuine-intent",
    "admissibility", "inadmissibility", "evidence strength",
    "eligibility fit", "document completeness", "refusal risk",
    "overstay", "ties assessment",
]

# Authoritative source feeds (RSS/Atom) for live policy bulletins.
RSS_FEEDS = [
    "https://www.uscis.gov/news/alerts/rss.xml",        # USCIS alerts
    "https://www.gov.uk/government/all.atom",           # UK gov (broad; filtered)
    "https://www.canada.ca/content/dam/ircc/migration/ircc-feeds/news-avis.xml",  # IRCC
]

# Search queries issued against the structured APIs.
QUERIES = [
    "visa refusal reasons statistics",
    "document checklist visa class update",
    "immigration policy change announcement",
    "genuine intent assessment criteria",
]

SOURCE_LABELS = {
    "crossref": "Crossref (official DOI metadata)",
    "semantic_scholar": "Semantic Scholar Graph API",
    "arxiv": "arXiv API",
    "rss": "Government RSS/Atom policy feeds",
}

DEFAULT_SOURCES = list(SOURCE_LABELS.keys())


# --------------------------------------------------------------------------- #
# HTTP helper (stdlib + optional requests)
# --------------------------------------------------------------------------- #
def _get(url: str, params: Optional[dict] = None, headers: Optional[dict] = None,
         timeout: float = 20.0) -> str:
    full = url
    if params:
        full = f"{url}?{urllib.parse.urlencode(params)}"
    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json,application/atom+xml,application/xml,text/xml,*/*"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(full, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} for {full}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error for {full}: {e.reason}") from e


# --------------------------------------------------------------------------- #
# Candidate entry model
# --------------------------------------------------------------------------- #
@dataclass
class Entry:
    title: str
    authors: str
    year: int
    venue: str
    url: str
    abstract: str
    source: str

    def to_dict(self) -> dict:
        return asdict(self)


def _hash(url: str) -> str:
    return hashlib.sha256((url or "").strip().lower().encode("utf-8")).hexdigest()[:16]


def score_entry(entry: Entry) -> float:
    """Recency + domain-keyword relevance score in [0, 1]."""
    now = dt.date.today().year
    try:
        year = int(entry.year) if entry.year else 0
    except (TypeError, ValueError):
        year = 0
    recency = max(0.0, 1.0 - (now - year) / 10.0) if year else 0.3
    text = f"{entry.title} {entry.abstract}".lower()
    hits = sum(1 for k in DOMAIN_KEYWORDS if k in text)
    relevance = min(1.0, hits / max(1, len(DOMAIN_KEYWORDS)))
    return round(0.5 * recency + 0.5 * relevance, 3)


# --------------------------------------------------------------------------- #
# Source adapters
# --------------------------------------------------------------------------- #
def _author_list_to_str(authors: Iterable) -> str:
    names = []
    for a in authors:
        if isinstance(a, str):
            names.append(a)
        elif isinstance(a, dict):
            n = a.get("name") or a.get("given", "") + " " + a.get("family", "")
            if n.strip():
                names.append(n.strip())
    return "; ".join(names)


def fetch_crossref(query: str, limit: int) -> List[Entry]:
    out: List[Entry] = []
    params = {"query": query, "rows": str(limit), "select": "title,author,published-print,published-online,container-title,URL,abstract"}
    try:
        raw = _get("https://api.crossref.org/works", params=params,
                   headers={"Accept": "application/json"})
        data = json.loads(raw)
    except (RuntimeError, json.JSONDecodeError) as e:
        print(f"[warn] crossref failed for {query!r}: {e}", file=sys.stderr)
        return out
    for item in data.get("message", {}).get("items", []):
        titles = item.get("title") or []
        title = titles[0] if titles else ""
        if not title:
            continue
        pub = item.get("published-print") or item.get("published-online") or {}
        year = (pub.get("date-parts", [[None]])[0] or [None])[0] or 0
        out.append(Entry(
            title=title,
            authors=_author_list_to_str(item.get("author", [])),
            year=int(year) if year else 0,
            venue=(item.get("container-title") or [""])[0],
            url=item.get("URL", ""),
            abstract=(item.get("abstract") or "")[:500],
            source="crossref",
        ))
    return out


def fetch_semantic_scholar(query: str, limit: int) -> List[Entry]:
    out: List[Entry] = []
    params = {"query": query, "limit": str(limit), "fields": "title,authors,year,venue,externalIds,abstract"}
    try:
        raw = _get("https://api.semanticscholar.org/graph/v1/paper/search", params=params)
        data = json.loads(raw)
    except (RuntimeError, json.JSONDecodeError) as e:
        print(f"[warn] semantic_scholar failed for {query!r}: {e}", file=sys.stderr)
        return out
    for item in data.get("data", []) or []:
        title = item.get("title") or ""
        if not title:
            continue
        ext = item.get("externalIds") or {}
        url = f"https://www.semanticscholar.org/paper/{item.get('paperId','')}"
        if ext.get("DOI"):
            url = f"https://doi.org/{ext['DOI']}"
        out.append(Entry(
            title=title,
            authors=_author_list_to_str(item.get("authors", [])),
            year=int(item.get("year") or 0),
            venue=item.get("venue", "") or "",
            url=url,
            abstract=(item.get("abstract") or "")[:500],
            source="semantic_scholar",
        ))
    return out


def fetch_arxiv(query: str, limit: int) -> List[Entry]:
    out: List[Entry] = []
    params = {"search_query": f"all:{query}", "start": "0", "max_results": str(limit),
              "sortBy": "submittedDate", "sortOrder": "descending"}
    try:
        raw = _get("http://export.arxiv.org/api/query", params=params)
    except RuntimeError as e:
        print(f"[warn] arxiv failed for {query!r}: {e}", file=sys.stderr)
        return out
    # Lightweight Atom parsing (avoid lxml dependency)
    entries = re.findall(r"<entry>(.*?)</entry>", raw, re.DOTALL)
    for block in entries:
        title = re.search(r"<title>(.*?)</title>", block, re.DOTALL)
        published = re.search(r"<published>(\d{4})", block)
        link = re.search(r'<id>(.*?)</id>', block)
        summary = re.search(r"<summary>(.*?)</summary>", block, re.DOTALL)
        if not title:
            continue
        out.append(Entry(
            title=html.unescape(re.sub(r"\s+", " ", title.group(1)).strip()),
            authors="",
            year=int(published.group(1)) if published else 0,
            venue="arXiv",
            url=html.unescape(link.group(1).strip()) if link else "",
            abstract=html.unescape(re.sub(r"\s+", " ", summary.group(1)).strip())[:500] if summary else "",
            source="arxiv",
        ))
    return out


def fetch_rss(limit: int) -> List[Entry]:
    out: List[Entry] = []
    for feed_url in RSS_FEEDS:
        try:
            raw = _get(feed_url)
        except RuntimeError as e:
            print(f"[warn] rss failed for {feed_url}: {e}", file=sys.stderr)
            continue
        items = re.findall(r"<item>(.*?)</item>", raw, re.DOTALL) or re.findall(r"<entry>(.*?)</entry>", raw, re.DOTALL)
        for block in items[:limit]:
            title = re.search(r"<title>(.*?)</title>", block, re.DOTALL)
            link = re.search(r"<link[^>]*>(.*?)</link>", block, re.DOTALL) or re.search(r'<link>(.*?)</link>', block)
            pub = re.search(r"<pubDate>(.*?)</pubDate>", block) or re.search(r"<published>(.*?)</published>", block)
            url = link.group(1).strip() if link else feed_url
            title_text = html.unescape(title.group(1).strip()) if title else "(untitled)"
            year = 0
            if pub:
                try:
                    year = dt.datetime.strptime(pub.group(1).strip()[:24], "%a, %d %b %Y %H:%M:%S").year
                except ValueError:
                    try:
                        year = int(re.match(r"(\d{4})", pub.group(1)).group(1))
                    except Exception:
                        year = dt.date.today().year
            if not year:
                year = dt.date.today().year
            out.append(Entry(
                title=title_text, authors="",
                year=year, venue=feed_url, url=url, abstract="", source="rss",
            ))
        time.sleep(0.5)  # be polite to government servers
    return out


ADAPTERS = {
    "crossref": lambda q, lim: fetch_crossref(q, lim),
    "semantic_scholar": lambda q, lim: fetch_semantic_scholar(q, lim),
    "arxiv": lambda q, lim: fetch_arxiv(q, lim),
    "rss": lambda q, lim: fetch_rss(lim),
}


# --------------------------------------------------------------------------- #
# Existing-hash loading & date filtering
# --------------------------------------------------------------------------- #
def load_existing_hashes(path: str) -> set:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    return set(re.findall(r"<!--hash:([0-9a-f]{16})-->", text))


def _parse_date(s: str) -> Optional[dt.date]:
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None


def since_filter(since: Optional[dt.date]):
    def keep(entry: Entry) -> bool:
        if since is None:
            return True
        try:
            y = int(entry.year)
        except (TypeError, ValueError):
            return False
        return y >= since.year
    return keep


# --------------------------------------------------------------------------- #
# Append to knowledge base
# --------------------------------------------------------------------------- #
def append_entries(entries: Sequence[Entry], path: str) -> int:
    existing = load_existing_hashes(path)
    today = dt.date.today().isoformat()
    lines, added = [], 0
    for e in sorted(entries, key=score_entry, reverse=True):
        h = _hash(e.url or e.title)
        if h in existing:
            continue
        existing.add(h)
        sc = score_entry(e)
        lines.append(
            f"- {today} | score={sc} | **{e.title}** | {e.authors} | {e.year} | "
            f"{e.venue} | {e.url} <!--hash:{h}-->"
        )
        added += 1
    if added:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n### Crawl {today} (+{added})\n" + "\n".join(lines) + "\n")
    print(f"[ok] appended {added} new entries to {path}")
    return added


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def crawl(sources: Sequence[str], limit: int, since: Optional[dt.date]) -> List[Entry]:
    keep = since_filter(since)
    results: List[Entry] = []
    for src in sources:
        adapter = ADAPTERS.get(src)
        if adapter is None:
            print(f"[warn] unknown source {src!r}; skipping", file=sys.stderr)
            continue
        if src == "rss":
            entries = adapter("", limit)
        else:
            entries = []
            for q in QUERIES:
                entries.extend(adapter(q, limit))
                time.sleep(0.5)  # respect public API rate limits
        results.extend(e for e in entries if keep(e))
        print(f"[info] {src}: {sum(1 for e in entries if keep(e))} candidates after filter")
    return results


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Grow SECOND-KNOWLEDGE-BRAIN.md from authoritative sources.")
    ap.add_argument("--dry-run", action="store_true", help="Print candidates as JSON; do not write.")
    ap.add_argument("--since", default=None, help="Only keep entries from this year onward (YYYY-MM-DD).")
    ap.add_argument("--limit", type=int, default=10, help="Max candidates per source/query.")
    ap.add_argument("--sources", default=",".join(DEFAULT_SOURCES),
                    help=f"Comma-separated subset of: {','.join(DEFAULT_SOURCES)}")
    ap.add_argument("--brain", default=BRAIN, help="Path to SECOND-KNOWLEDGE-BRAIN.md.")
    args = ap.parse_args(argv)

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    since = _parse_date(args.since)
    entries = crawl(sources, args.limit, since)

    if args.dry_run:
        print(json.dumps([{**e.to_dict(), "score": score_entry(e)} for e in entries], indent=2, ensure_ascii=False))
        return 0

    added = append_entries(entries, args.brain)
    print(f"[done] {added} entries appended.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
