"""Authored fictional showcase fixtures. No product, provider, model or DB imports."""
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
import re


START = date(2026, 10, 16)
END = date(2026, 10, 29)
SENTIMENTS = ("Positive", "Neutral", "Negative")
SECTORS = ("Technology", "Healthcare", "Financials", "Energy", "Materials", "Consumer")


@dataclass(frozen=True)
class Example:
    article_id: str
    company: str
    sector: str
    source: str
    day: date
    title: str
    summary: str
    sentiment: str
    candidate: str
    synthetic: bool = True


def examples():
    """Labels and relationships are illustrative, not inferred or collected."""
    stories = (
        ("Aster Circuits", "Technology", (
            ("Positive", "Aster Circuits expands its fictional chip laboratory"),
            ("Positive", "Aster Circuits presents a new research facility"),
            ("Negative", "Aster Circuits reports higher component costs"),
            ("Neutral", "Aster Circuits schedules a product briefing"))),
        ("Cedar Therapeutics", "Healthcare", (
            ("Positive", "Cedar Therapeutics opens a fictional research centre"),
            ("Neutral", "Cedar Therapeutics publishes its research calendar"),
            ("Positive", "Cedar Therapeutics expands a laboratory partnership"),
            ("Negative", "Cedar Therapeutics revises a project timetable"))),
        ("Harbor Ledger Bank", "Financials", (
            ("Neutral", "Harbor Ledger Bank announces an investor meeting"),
            ("Positive", "Harbor Ledger Bank introduces a fictional savings tool"),
            ("Negative", "Harbor Ledger Bank describes rising operating costs"),
            ("Positive", "Harbor Ledger Bank expands its digital service"))),
        ("Solstice Solarworks", "Energy", (
            ("Positive", "Solstice Solarworks wins a fictional supply contract"),
            ("Positive", "Solstice Solarworks outlines a supply agreement"),
            ("Neutral", "Solstice Solarworks publishes an operations calendar"),
            ("Negative", "Solstice Solarworks reports installation delays"))),
        ("Copperleaf Minerals", "Materials", (
            ("Negative", "Copperleaf Minerals describes higher transport costs"),
            ("Neutral", "Copperleaf Minerals schedules its annual update"),
            ("Positive", "Copperleaf Minerals improves a fictional recycling line"),
            ("Positive", "Copperleaf Minerals completes a processing upgrade"))),
        ("Maple Commerce", "Consumer", (
            ("Positive", "Maple Commerce launches a fictional store format"),
            ("Neutral", "Maple Commerce publishes its store calendar"),
            ("Negative", "Maple Commerce reports a short-term logistics delay"),
            ("Neutral", "Maple Commerce announces its next briefing"))),
    )
    # Distinct authored fictional context gives the showcase meaningful drill-down,
    # without implying these companies, events or business effects exist.
    context = (
        (
            "In this fictional scenario, the expansion increases chip prototype testing capacity. It is an announced plan, not an observed earnings outcome.",
            "This fictional facility announcement describes the same broad laboratory expansion theme as SYN-001; candidate overlap is illustrative only.",
            "A separate fictional update describes higher materials and packaging costs. It does not establish an effect on the laboratory project.",
            "The company announces the date of a product briefing but provides no new financial guidance.",
        ),
        (
            "The fictional research centre adds a testing location; the headline does not report clinical results.",
            "The company sets out its upcoming research calendar, with no approval or earnings figures.",
            "A fictional laboratory partner joins a joint research program; commercial impact is unknown.",
            "The fictional schedule change delays project milestones but does not quantify a financial loss.",
        ),
        (
            "This fictional notice schedules an investor event without new earnings information.",
            "The fictional savings feature expands digital options for customers; demand is not measured.",
            "The company describes cost pressure in its fictional operating update, distinct from its meeting notice.",
            "The bank introduces additional digital-service access in a separate fictional announcement.",
        ),
        (
            "A fictional supply-contract announcement describes a potential new order, not booked revenue.",
            "A second fictional report outlines the same broad supply theme without confirming identical event identity.",
            "This is a routine operational schedule, not a statement of financial performance.",
            "A separate fictional installation update describes delays to project delivery.",
        ),
        (
            "This fictional report discusses increased freight and transport expenses.",
            "The company schedules its annual update without reporting new results.",
            "A fictional recycling improvement reduces process waste; any financial effect is unspecified.",
            "The company completes a fictional processing-line upgrade as a distinct operational report.",
        ),
        (
            "A fictional retail format is introduced; this example does not report sales performance.",
            "The company schedules store operations updates without a financial forecast.",
            "A fictional logistics disruption delays deliveries; its financial effect is unknown.",
            "The company announces the date of its next briefing without releasing new results.",
        ),
    )
    sources = ("Demo Wire", "Illustrative Ledger", "Fictional Finance Desk")
    records = []
    for company_index, (company, sector, items) in enumerate(stories):
        for position, (label, title) in enumerate(items):
            number = company_index * 4 + position + 1
            records.append(Example(
                f"SYN-{number:03}", company, sector, sources[number % 3],
                START + timedelta(days=(company_index * 2 + position * 3) % 14),
                title, context[company_index][position],
                label, f"C-{company_index + 1}-{0 if position < 2 else position}"))
    return tuple(records)


def select(records, start=START, end=END, sectors=(), sentiments=(), search=""):
    query = search.strip().casefold()
    return [r for r in records if start <= r.day <= end
            and (not sectors or r.sector in sectors)
            and (not sentiments or r.sentiment in sentiments)
            and query in " ".join((r.title, r.company, r.source, r.sector)).casefold()]



# A headline document-frequency cloud rather than decorative keywords or invented
# model weights. Generic language and fictional company-name tokens are excluded.
CLOUD_STOPWORDS = frozenset((
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "its",
    "new", "next", "of", "on", "the", "to", "with", "this", "that", "their",
    "fictional", "reports", "publishes", "announces", "describes", "presents",
    "schedules", "outlines", "introduces", "said", "will", "company", "example",
    "headline", "headlines", "news", "report", "update", "updates",
))


def word_cloud_terms(records, limit=16):
    """Count example headlines containing each term, once per article.

    The values are NOT model salience, market impact or real news frequency.
    """
    if limit < 1:
        return []
    counts, evidence = Counter(), {}
    for row in records:
        company_words = set(re.findall(r"[a-z]+", row.company.casefold()))
        words = set(re.findall(r"[a-z]+", row.title.casefold()))
        words = {word for word in words
                 if len(word) > 2 and word not in CLOUD_STOPWORDS
                 and word not in company_words}
        for word in words:
            counts[word] += 1
            evidence.setdefault(word, []).append(row.article_id)
    ranked = sorted(counts, key=lambda word: (-counts[word], word))[:limit]
    return [{"term": word, "count": counts[word],
             "article_ids": tuple(sorted(evidence[word]))} for word in ranked]


def _spaced(index, total, low=14, high=86):
    return (low + high) / 2 if total == 1 else low + (high - low) * index / (total - 1)


def graph_overview(records):
    """Aggregated industry-company-source links, grounded only in fixtures."""
    if not records:
        return {"nodes": [], "edges": []}
    nodes, edges = {}, []
    sectors = [sector for sector in SECTORS if any(r.sector == sector for r in records)]
    companies = sorted({r.company for r in records})
    sources = sorted({r.source for r in records})
    for i, sector in enumerate(sectors):
        nodes["sector:" + sector] = dict(id="sector:" + sector, name=sector,
            label=sector, kind="Industry", detail="Fictional industry classification",
            x=10, y=_spaced(i, len(sectors)))
    for i, company in enumerate(companies):
        company_rows = [r for r in records if r.company == company]
        nodes["company:" + company] = dict(id="company:" + company, name=company,
            label=company, kind="Company",
            detail=f"{len(company_rows)} authored fictional reports",
            x=51, y=_spaced(i, len(companies)))
    for i, source in enumerate(sources):
        nodes["source:" + source] = dict(id="source:" + source, name=source,
            label=source, kind="Source", detail="Fictional reporting source",
            x=91, y=_spaced(i, len(sources), 22, 78))
    for company in companies:
        company_rows = [r for r in records if r.company == company]
        for sector in sorted({r.sector for r in company_rows}):
            subset = [r for r in company_rows if r.sector == sector]
            edges.append(dict(from_id="sector:" + sector, to_id="company:" + company,
                relationship="Illustrative industry classification", count=len(subset),
                article_id=subset[0].article_id, article_ids=tuple(r.article_id for r in subset)))
        for source in sorted({r.source for r in company_rows}):
            subset = [r for r in company_rows if r.source == source]
            edges.append(dict(from_id="company:" + company, to_id="source:" + source,
                relationship="Fictional source reports on company", count=len(subset),
                article_id=subset[0].article_id, article_ids=tuple(r.article_id for r in subset)))
    for edge in edges:
        edge.update({"from": edge["from_id"], "to": edge["to_id"]})
        left, right = nodes[edge["from_id"]], nodes[edge["to_id"]]
        edge.update(x=left["x"], y=left["y"], x2=right["x"], y2=right["y"])
    return {"nodes": list(nodes.values()), "edges": edges}


def graph(records, company):
    """Focused, layered evidence graph; never a verified event-identity model."""
    rows = sorted((r for r in records if r.company == company),
                  key=lambda r: (r.day, r.article_id))
    if not rows:
        return {"nodes": [], "edges": []}
    nodes, edges = {}, []

    def add(node_id, name, kind, detail):
        nodes.setdefault(node_id, dict(id=node_id, name=name, label=name,
                                       kind=kind, detail=detail))
        return node_id

    def edge(left, right, relationship, article_id):
        # Keep the previously tested from/to schema while supporting explicit IDs.
        edges.append({"from_id": left, "to_id": right, "from": left, "to": right,
                      "relationship": relationship, "count": 1, "article_id": article_id})

    company_id = add("company", company, "Company",
                     f"{len(rows)} fictional source reports")
    industry_id = add("sector:" + rows[0].sector, rows[0].sector, "Industry",
                      "Illustrative sector assignment")
    edge(industry_id, company_id, "Illustrative sector assignment", rows[0].article_id)
    for row in rows:
        article_id = add(row.article_id, row.article_id, "Article",
                         f"{row.day.isoformat()} · {row.title} · {row.sentiment}")
        nodes[article_id].update(article_id=row.article_id, title=row.title, summary=row.summary,
            company=row.company, industry=row.sector, sentiment=row.sentiment,
            source=row.source, candidate=row.candidate)
        source_id = add("source:" + row.source, row.source, "Source",
                        "Fictional publication/source")
        candidate_id = add(row.candidate, row.candidate, "Unverified candidate",
                           "Illustrative grouping only; not confirmed event identity")
        edge(company_id, article_id, "Company appears in fictional article", row.article_id)
        edge(article_id, candidate_id, "Unverified candidate membership", row.article_id)
        edge(article_id, source_id, "Fictional publication source", row.article_id)

    nodes[company_id].update(x=10, y=53)
    nodes[industry_id].update(x=10, y=10)
    article_ids = [r.article_id for r in rows]
    for i, node_id in enumerate(article_ids):
        nodes[node_id].update(x=39, y=_spaced(i, len(article_ids)))
    candidates = sorted({r.candidate for r in rows})
    for candidate in candidates:
        ys = [nodes[r.article_id]["y"] for r in rows if r.candidate == candidate]
        nodes[candidate].update(x=67, y=sum(ys) / len(ys),
                                 detail=f"{len(ys)} illustrative member report(s); not verified")
    sources = sorted({r.source for r in rows})
    for i, source in enumerate(sources):
        nodes["source:" + source].update(x=92, y=_spaced(i, len(sources), 18, 82))
    for item in edges:
        left, right = nodes[item["from_id"]], nodes[item["to_id"]]
        item.update(x=left["x"], y=left["y"], x2=right["x"], y2=right["y"])
    return {"nodes": list(nodes.values()), "edges": edges}
