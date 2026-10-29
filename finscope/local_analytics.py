"""One raw-article counting/filter contract for every local dashboard view."""
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

from .demo_pipeline import classify_sectors
from .ui_data import SECTORS, SENTIMENTS


def model_key(analysis):
    return f"{analysis.family} · {analysis.model_id} · {analysis.revision}"


@dataclass(frozen=True)
class Filters:
    start: date | None = None
    end: date | None = None
    sectors: tuple = ()
    sources: tuple = ()
    sentiments: tuple = ()
    models: tuple = ()
    search: str = ""
    include_unknown_dates: bool = False


def select_articles(news, analyses, filters):
    if filters.start and filters.end and filters.start > filters.end:
        raise ValueError("Start date must be no later than end date")
    # Latest matching model per original; reanalysis never multiplies article counts.
    latest = {}
    for analysis in sorted(analyses, key=lambda a: (a.analyzed_at, a.analysis_id)):
        if not filters.models or model_key(analysis) in filters.models:
            latest[analysis.article_id] = analysis
    selected = []
    for item in news:
        result = latest.get(item.article_id)
        day = date.fromisoformat(item.record_date) if item.record_date else None
        if day is None and (filters.start or filters.end) and not filters.include_unknown_dates:
            continue
        if day is not None and (filters.start and day < filters.start or filters.end and day > filters.end):
            continue
        if filters.sectors and not set(filters.sectors).intersection(item.sectors):
            continue
        if filters.sources and item.source not in filters.sources:
            continue
        if filters.sentiments and (result is None or result.label not in filters.sentiments):
            continue
        if filters.models and result is None:
            continue
        if filters.search.casefold() not in " ".join((item.title, item.summary, item.source, item.company)).casefold():
            continue
        selected.append(item)
    return selected, {n.article_id: latest[n.article_id] for n in selected if n.article_id in latest}


def overview_counts(news, results):
    labels = Counter(a.label for a in results.values())
    return {"raw_articles": len(news), "analyzed": len(results),
            "sources": len({n.source for n in news}), "unanalysed": len(news)-len(results),
            **{s: labels[s] for s in SENTIMENTS}}


def sector_counts(news, results):
    return [{"Sector": sector, **{label: sum(sector in n.sectors and n.article_id in results
                 and results[n.article_id].label == label for n in news) for label in SENTIMENTS},
             "Not analyzed": sum(sector in n.sectors and n.article_id not in results for n in news)} for sector in SECTORS]


def daily_counts(news, results, start, end):
    if start > end or (end-start).days > 3660:
        raise ValueError("Choose a date range of at most 10 years")
    rows = []
    day = start
    while day <= end:
        values = [n for n in news if n.record_date == day.isoformat()]
        rows.append({"Date": day.isoformat(), **{s: sum(n.article_id in results and results[n.article_id].label == s
                        for n in values) for s in SENTIMENTS},
                     "Not analyzed": sum(n.article_id not in results for n in values)})
        day += timedelta(days=1)
    return rows


def heatmap_cells(news, results, start, end, sectors=SECTORS):
    if start > end or (end-start).days > 366:
        raise ValueError("Heatmap supports at most 367 daily columns; narrow the date range")
    cells = []
    day = start
    while day <= end:
        for sector in sectors:
            records = [n for n in news if n.record_date == day.isoformat() and sector in n.sectors]
            labels = Counter(results[n.article_id].label for n in records if n.article_id in results)
            total, count = len(records), sum(labels.values())
            cells.append({"Date": day.isoformat(), "Sector": sector, "Articles": total,
                "Analyzed": count, "Positive": labels["Positive"], "Neutral": labels["Neutral"], "Negative": labels["Negative"],
                "Balance": (labels["Positive"]-labels["Negative"])/count if count else None,
                "Sample": "No local records" if not total else "No analysis" if not count else "Low sample (n<3)" if count < 3 else "n≥3 (not statistical validation)"})
        day += timedelta(days=1)
    return cells


def evidence_graph(news, results):
    nodes, edges = {}, []
    group_counts = Counter(a.candidate_id for a in results.values() if a.candidate_id)
    def node(identity, kind, label, article_id=""):
        nodes.setdefault(identity, {"id": identity, "kind": kind, "label": label,
                                   "display_label": label[:23]+"…" if len(label)>24 else label,
                                   "article_id": article_id})
    def edge(article_id, target, relation, evidence):
        edges.append({"from": "article:"+article_id, "to": target, "relationship": relation,
                      "evidence": evidence, "article_id": article_id})
    for item in news:
        node("article:"+item.article_id, "Article", item.title, item.article_id)
        source = "source:"+item.source
        node(source, "Source", item.source)
        edge(item.article_id, source, "provider_source", "Original provider/collector source metadata")
        sector_evidence = classify_sectors(item.analysis_text)
        for sector in item.sectors:
            identity = "sector:"+sector
            node(identity, "Sector", sector)
            edge(item.article_id, identity, "keyword_sector", ", ".join(sector_evidence.get(sector, [])) or "No keyword match; Unclassified")
        if item.company:
            identity = "company:"+item.company
            node(identity, "Company query", item.company)
            edge(item.article_id, identity, "returned_for_ticker", "Ticker-specific company-news query; not a verified company mention or causal link")
        result = results.get(item.article_id)
        if result and result.candidate_id and group_counts[result.candidate_id] > 1:
            identity = "candidate:"+result.candidate_id
            node(identity, "Unverified candidate", "Candidate "+result.candidate_id[:6])
            edge(item.article_id, identity, "unverified_cosine_candidate", f"MiniLM {result.embedding_revision}; predeclared cosine/time rule, not confirmed event identity")
    columns = {"Source": 0, "Sector": 1, "Article": 2, "Company query": 3, "Unverified candidate": 4}
    for kind, column in columns.items():
        members = [n for n in nodes.values() if n["kind"] == kind]
        for index, member in enumerate(members):
            member.update(x=column, y=(index+1)/(len(members)+1))
    for relation in edges:
        left, right = nodes[relation["from"]], nodes[relation["to"]]
        relation.update(x=left["x"], y=left["y"], x2=right["x"], y2=right["y"])
    return {"nodes": list(nodes.values()), "edges": edges}
