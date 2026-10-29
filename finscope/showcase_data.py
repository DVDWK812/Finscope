"""Authored fictional showcase fixtures. No product, provider, model or DB imports."""
from dataclasses import dataclass
from datetime import date, timedelta
import math


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
    sources = ("Demo Wire", "Illustrative Ledger", "Fictional Finance Desk")
    records = []
    for company_index, (company, sector, items) in enumerate(stories):
        for position, (label, title) in enumerate(items):
            number = company_index * 4 + position + 1
            records.append(Example(
                f"SYN-{number:03}", company, sector, sources[number % 3],
                START + timedelta(days=(company_index * 2 + position * 3) % 14),
                title, "An authored fictional example for interface exploration. "
                "The sentiment label and relationships are illustrative; no model was run.",
                label, f"C-{company_index + 1}-{0 if position < 2 else position}"))
    return tuple(records)


def select(records, start=START, end=END, sectors=(), sentiments=(), search=""):
    query = search.strip().casefold()
    return [r for r in records if start <= r.day <= end
            and (not sectors or r.sector in sectors)
            and (not sentiments or r.sentiment in sentiments)
            and query in " ".join((r.title, r.company, r.source, r.sector)).casefold()]


def graph(records, company):
    """All nodes/edges refer only to authored entities, never real-world claims."""
    records = [r for r in records if r.company == company]
    nodes, edges = {}, []

    def add(node_id, name, kind):
        nodes.setdefault(node_id, {"id": node_id, "name": name, "kind": kind})
        return node_id

    def edge(left, right, relationship, article_id):
        edges.append({"from": left, "to": right, "relationship": relationship,
                      "article_id": article_id})

    if not records:
        return {"nodes": [], "edges": []}
    company_id = add("company", company, "Company")
    for row in records:
        article = add(row.article_id, row.article_id, "Article")
        industry = add("sector:" + row.sector, row.sector, "Industry")
        source = add("source:" + row.source, row.source, "Source")
        candidate = add(row.candidate, row.candidate, "Unverified candidate")
        for left, right, relationship in (
                (company_id, article, "Fictional company mentioned"),
                (article, industry, "Illustrative industry tag"),
                (article, source, "Fictional source"),
                (article, candidate, "Illustrative candidate membership")):
            edge(left, right, relationship, row.article_id)
    for index, node in enumerate(nodes.values()):
        angle = 2 * math.pi * index / len(nodes)
        node.update(x=50 + 38 * math.cos(angle), y=50 + 38 * math.sin(angle))
    for item in edges:
        left, right = nodes[item["from"]], nodes[item["to"]]
        item.update(x=left["x"], y=left["y"], x2=right["x"], y2=right["y"])
    return {"nodes": list(nodes.values()), "edges": edges}
