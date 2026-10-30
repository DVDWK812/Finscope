"""Self-contained markup for authored fictional previews; no scripts or I/O."""
from html import escape
import math
import textwrap


NODE_COLORS = {"Industry": "#e9c776", "Company": "#60e5bc", "Article": "#9dbfff",
               "Unverified candidate": "#d4adff", "Source": "#f69e9e"}
SENTIMENT_COLORS = {"Positive": "#60e5bc", "Neutral": "#b8c7dc", "Negative": "#ff9b93"}


def visible_graph(data, include_sources=True):
    nodes = [n for n in data["nodes"] if include_sources or n["kind"] != "Source"]
    ids = {n["id"] for n in nodes}
    return {"nodes": nodes, "edges": [e for e in data["edges"]
            if e["from_id"] in ids and e["to_id"] in ids]}


def relation_style(relationship):
    text = relationship.casefold()
    if "candidate" in text:
        return "candidate", "Candidate membership · unverified", "#c6a4f1", "5 4"
    if "source" in text:
        return "source", "Fictional reporting source", "#e9a09d", ""
    if "sector" in text or "industry" in text:
        return "industry", "Illustrative industry tag", "#d9c378", ""
    return "mention", "Company mentioned in article", "#66cdb0", ""


def relationship_markup(data, height=520):
    """A bounded scrolling canvas preserves label size on narrow screens."""
    width = 860
    styles = {relation_style(e["relationship"]) for e in data["edges"]}
    svg = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           'role="img" aria-label="Fictional company, industry, article, candidate and source relationships" '
           'xmlns="http://www.w3.org/2000/svg"><defs>']
    for key, _, color, _ in sorted(styles):
        svg.append(f'<marker id="fs-arrow-{key}" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">'
                   f'<path d="M0,0 L7,3.5 L0,7" fill="{color}"/></marker>')
    svg.append('</defs>')
    positions = {n["id"]: (45 + n["x"] * (width - 90) / 100,
                             25 + n["y"] * (height - 95) / 100) for n in data["nodes"]}
    for edge in data["edges"]:
        x, y = positions[edge["from_id"]]
        x2, y2 = positions[edge["to_id"]]
        distance = max(1, math.hypot(x2 - x, y2 - y))
        dx, dy = (x2 - x) / distance, (y2 - y) / distance
        x, y, x2, y2 = x + 14 * dx, y + 14 * dy, x2 - 17 * dx, y2 - 17 * dy
        mid = (x + x2) / 2
        key, _, color, dash = relation_style(edge["relationship"])
        headlines = "; ".join(edge.get("headlines", ()))
        title = escape(f'{edge["relationship"]} · {edge["count"]} fictional report(s) · {headlines}')
        svg.append(f'<path d="M{x:.1f},{y:.1f} C{mid:.1f},{y:.1f} {mid:.1f},{y2:.1f} {x2:.1f},{y2:.1f}" '
                   f'fill="none" stroke="{color}" stroke-width="{min(2.6, 1.4 + .2 * edge["count"]):.1f}" '
                   f'stroke-opacity=".78" stroke-dasharray="{dash}" marker-end="url(#fs-arrow-{key})"><title>{title}</title></path>')
    for node in data["nodes"]:
        x, y = positions[node["id"]]
        fields = [node["name"], node["kind"], node.get("detail", "")]
        if node["kind"] == "Article":
            fields = [node.get(key, "") for key in
                      ("title", "company", "industry", "sentiment", "published", "source", "summary")]
        svg.append(f'<g><title>{escape(" · ".join(filter(None, fields)))}</title>'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="{NODE_COLORS[node["kind"]]}" stroke="#0c1423" stroke-width="2"/>')
        lines = textwrap.wrap(node["label"], width=24 if node["kind"] == "Article" else 22)
        if node["kind"] == "Article":
            lines.append(node["sentiment"] + " sentiment")
        elif node["kind"] == "Unverified candidate":
            lines.append("Unverified candidate")
        for index, line in enumerate(lines):
            tone = node["kind"] == "Article" and index == len(lines) - 1
            color = SENTIMENT_COLORS[node["sentiment"]] if tone else "#e1eafa"
            svg.append(f'<text x="{x:.1f}" y="{y + 27 + index * 15:.1f}" text-anchor="middle" '
                       f'font-family="system-ui,sans-serif" font-size="12" font-weight="{650 if tone else 400}" '
                       f'fill="{color}">{escape(line)}</text>')
        svg.append('</g>')
    svg.append('</svg>')
    nodes = ''.join(f'<span><i style="background:{color}"></i>{escape(kind)}</span>'
                    for kind, color in NODE_COLORS.items() if any(n["kind"] == kind for n in data["nodes"]))
    lines = ''.join(f'<span><b style="border-top:2px {"dashed" if dash else "solid"} {color}"></b>{escape(label)}</span>'
                    for _, label, color, dash in sorted(styles))
    return '''<style>
    .fs-graph-scroll{max-width:100%;overflow-x:auto;border:1px solid #30415a;border-radius:14px;background:#101b2d;}
    .fs-graph-scroll svg{display:block;min-width:860px;}
    .fs-map-key{display:flex;flex-wrap:wrap;gap:.6rem 1.1rem;color:#c6d4e7;font:12px/1.5 system-ui,sans-serif;margin:.8rem 0;}
    .fs-map-key span{display:inline-flex;align-items:center;gap:.45rem;}
    .fs-map-key i{width:9px;height:9px;border-radius:50%;display:inline-block;}
    .fs-map-key b{width:24px;display:inline-block;}
    </style><div class="fs-graph-scroll" role="region" tabindex="0" aria-label="Relationship map; scroll horizontally on a small screen">''' + ''.join(svg) + f'</div><div class="fs-map-key">{nodes}</div><div class="fs-map-key">{lines}</div>'


def word_cloud_markup(terms):
    words = []
    for item in terms:
        count = item["count"]
        label = escape(f'{item["term"]}: {count} fictional headline(s)', quote=True)
        words.append(f'<span role="listitem" aria-label="{label}" title="{label}" '
                     f'style="font-size:{min(32, 18 + 5 * (count - 1))}px;'
                     f'color:{"#60e5bc" if count > 1 else "#b5c9e2"}">{escape(item["term"])}'
                     f'<sup>{count}</sup></span>')
    return '''<style>
    .fs-word-cloud{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:center;gap:.65rem 1.15rem;
      padding:1.2rem .8rem;border:1px solid #30415a;border-radius:14px;background:#101b2d;}
    .fs-word-cloud span{display:inline-flex;align-items:baseline;gap:.2rem;max-width:100%;line-height:1.6;
      font-family:system-ui,sans-serif;font-weight:650;overflow-wrap:anywhere;}
    .fs-word-cloud sup{font-size:11px;font-weight:400;color:#a9bdd5;}
    </style><div class="fs-word-cloud" role="list" aria-label="Authored headline word frequencies">''' + ''.join(words) + '</div>'
