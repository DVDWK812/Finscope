"""Self-contained authored previews; UI-only mobile positioning, no network I/O."""
from html import escape
import textwrap


from .showcase_theme import TOKENS, SENTIMENT_COLORS

NODE_COLORS = {"Industry": TOKENS["industry"], "Company": TOKENS["accent"], "Article": "#9dbfff",
               "Unverified candidate": TOKENS["candidate"], "Source": TOKENS["source"]}


def visible_graph(data, include_sources=True):
    nodes = [n for n in data["nodes"] if include_sources or n["kind"] != "Source"]
    ids = {n["id"] for n in nodes}
    return {"nodes": nodes, "edges": [e for e in data["edges"]
            if e["from_id"] in ids and e["to_id"] in ids]}


def relation_style(relationship):
    text = relationship.casefold()
    if "candidate" in text:
        return "candidate", "Candidate membership · unverified", TOKENS["candidate"], "5 4"
    if "source" in text:
        return "source", "Fictional reporting source", TOKENS["source"], ""
    if "sector" in text or "industry" in text:
        return "industry", "Illustrative industry tag", TOKENS["industry"], ""
    return "mention", "Company mentioned in article", TOKENS["accent"], ""


def graph_layout(data):
    """Presentation coordinates only; never changes nodes or membership."""
    kinds = {kind: [n for n in data["nodes"] if n["kind"] == kind] for kind in NODE_COLORS}
    articles, sources, candidates = kinds["Article"], kinds["Source"], kinds["Unverified candidate"]
    positions, sizes = {}, {}
    if articles:
        width = 1110 if sources and candidates else 960 if sources or candidates else 760
        height = max(390, 94 * len(articles) + 20)
        middle = height / 2
        for node in kinds["Industry"]:
            positions[node["id"]], sizes[node["id"]] = (65, middle), (110, 48)
        for node in kinds["Company"]:
            positions[node["id"]], sizes[node["id"]] = (245, middle), (156, 66)
        ordered = sorted(articles, key=lambda n: n["y"])
        for i, node in enumerate(ordered):
            positions[node["id"]], sizes[node["id"]] = (530 if sources or candidates else 590, 53 + 94 * i), (212, 70)
        for node in candidates:
            members = [positions[e["from_id"]][1] for e in data["edges"] if e["to_id"] == node["id"]]
            positions[node["id"]], sizes[node["id"]] = (830, sum(members) / len(members)), (184, 78)
        for i, node in enumerate(sources):
            positions[node["id"]], sizes[node["id"]] = (1030 if candidates else 850, 60 + i * (height - 120) / max(1, len(sources) - 1)), (138, 62)
    else:
        width, height = (900 if sources else 660), 400
        columns = {"Industry": 85, "Company": 385, "Source": 800}
        for kind in ("Industry", "Company", "Source"):
            for i, node in enumerate(kinds[kind]):
                y = 40 + i * (height - 80) / max(1, len(kinds[kind]) - 1)
                positions[node["id"]], sizes[node["id"]] = (columns[kind], y), (146 if kind == "Industry" else 174, 48)
    return width, height, positions, sizes


def relationship_markup(data, height=None, mobile_zoom=1.0):
    """Fit desktop width; retain readable, keyboard-pannable mobile geometry."""
    width, height, positions, sizes = graph_layout(data)
    styles = {relation_style(e["relationship"]) for e in data["edges"]}
    svg = [f'<svg viewBox="0 0 {width} {height}" role="img" '
           'aria-label="Fictional company, industry, article, candidate and source relationships" '
           'xmlns="http://www.w3.org/2000/svg"><defs>']
    for key, _, color, _ in sorted(styles):
        svg.append(f'<marker id="fs-arrow-{key}" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">'
                   f'<path d="M0,0 L6,3 L0,6" fill="{color}"/></marker>')
    svg.append('</defs>')
    for edge in data["edges"]:
        x, y = positions[edge["from_id"]]
        x2, y2 = positions[edge["to_id"]]
        x += sizes[edge["from_id"]][0] / 2 + 2
        x2 -= sizes[edge["to_id"]][0] / 2 + 9
        mid = (x + x2) / 2
        key, _, color, dash = relation_style(edge["relationship"])
        headlines = "; ".join(edge.get("headlines", ()))
        title = escape(f'{edge["relationship"]} · {edge["count"]} fictional report(s) · {headlines}')
        svg.append(f'<path d="M{x:.1f},{y:.1f} C{mid:.1f},{y:.1f} {mid:.1f},{y2:.1f} {x2:.1f},{y2:.1f}" '
                   f'fill="none" stroke="{color}" stroke-width="1.5" stroke-opacity=".7" '
                   f'stroke-dasharray="{dash}" marker-end="url(#fs-arrow-{key})"><title>{title}</title></path>')
    for node in data["nodes"]:
        x, y = positions[node["id"]]
        w, h = sizes[node["id"]]
        fields = [node["name"], node["kind"], node.get("detail", "")]
        article = node["kind"] == "Article"
        candidate = node["kind"] == "Unverified candidate"
        if article:
            fields = [node.get(key, "") for key in ("title", "company", "industry", "sentiment", "published", "source", "summary")]
        title = escape(" · ".join(filter(None, fields)), quote=True)
        color = NODE_COLORS[node["kind"]]
        svg.append(f'<g class="fs-node" tabindex="0" role="img" aria-label="{title}"><title>{title}</title>'
                   f'<rect x="{x-w/2:.1f}" y="{y-h/2:.1f}" width="{w}" height="{h}" rx="9" '
                   f'fill="{TOKENS["raised"]}" stroke="{color}" stroke-opacity=".55"/>')
        lines = textwrap.wrap(node["label"], width=28 if article else 23)
        first = y - (len(lines) - 1) * 8 - (5 if article or candidate else -4)
        for i, line in enumerate(lines):
            svg.append(f'<text x="{x:.1f}" y="{first+i*16:.1f}" text-anchor="middle" '
                       f'font-family="system-ui,sans-serif" font-size="13" fill="{TOKENS["text"]}">{escape(line)}</text>')
        if article or candidate:
            label = node["sentiment"] + " sentiment" if article else "Unverified candidate"
            tone = SENTIMENT_COLORS[node["sentiment"]] if article else color
            svg.append(f'<text x="{x:.1f}" y="{y+h/2-11:.1f}" text-anchor="middle" '
                       f'font-family="system-ui,sans-serif" font-size="11" font-weight="600" fill="{tone}">{escape(label)}</text>')
        svg.append('</g>')
    svg.append('</svg>')
    mobile_width = int(width * max(1.0, min(1.5, mobile_zoom)))
    anchor = next((positions[n["id"]][0] for n in data["nodes"] if n["kind"] == "Article"), width / 2)
    mobile_position = f'''<script>
    (() => {{
      const panel = document.querySelector('.fs-graph-scroll');
      const position = () => {{panel.scrollLeft = innerWidth <= 640
        ? Math.max(0, {anchor * mobile_width / width:.1f} - panel.clientWidth / 2) : 0;}};
      requestAnimationFrame(position);
      addEventListener('resize', position);
    }})();
    </script>'''
    return f'''<style>
    .fs-graph-scroll{{max-width:100%;overflow:auto;background:{TOKENS["surface"]};border-radius:10px;touch-action:pan-x pan-y;}}
    .fs-graph-scroll svg{{display:block;width:100%;height:auto;max-height:400px;}}
    .fs-node:focus{{outline:none;}}.fs-node:focus rect{{stroke:{TOKENS["accent"]};stroke-width:3;stroke-opacity:1;}}
    .fs-map-key{{display:flex;flex-wrap:wrap;gap:8px 20px;color:{TOKENS["muted"]};font:11px/1.5 system-ui,sans-serif;padding:8px 0;}}
    .fs-map-key span{{display:inline-flex;align-items:center;gap:7px;}}.fs-map-key b{{width:20px;display:inline-block;border-top:1px solid #7d9f9b;}}
    @media(max-width:640px){{.fs-graph-scroll svg{{width:{mobile_width}px;min-width:{mobile_width}px;max-height:none;}}}}
    </style><div class="fs-graph-scroll" role="region" tabindex="0" aria-label="Relationship map; scroll horizontally on a small screen">''' + ''.join(svg) + (
        '<div class="fs-map-key"><span><b></b>Article context</span>'
        + ('<span><b style="border-top-style:dashed;border-color:#c8b5ed"></b>Unverified topic link</span>' if any(n["kind"] == "Unverified candidate" for n in data["nodes"]) else '')
        + '</div>' + mobile_position)


def word_cloud_markup(terms):
    words = []
    for item in terms:
        count = item["count"]
        label = escape(f'{item["term"]}: {count} fictional headline(s)', quote=True)
        words.append(f'<span role="listitem" aria-label="{label}" title="{label}" '
                     f'style="font-size:{min(32, 18 + 5 * (count - 1))}px;'
                     f'color:{TOKENS["accent"] if count > 1 else TOKENS["muted"]}">{escape(item["term"])}'
                     f'<sup>{count}</sup></span>')
    return f'''<style>
    .fs-word-cloud{{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:center;gap:.7rem 1.3rem;
      padding:1.5rem 1rem;border:1px solid {TOKENS["border"]};border-radius:12px;background:{TOKENS["raised"]};}}
    .fs-word-cloud span{{display:inline-flex;align-items:baseline;gap:.2rem;max-width:100%;line-height:1.6;
      font-family:system-ui,sans-serif;font-weight:600;overflow-wrap:anywhere;}}
    .fs-word-cloud sup{{font-size:11px;font-weight:400;color:{TOKENS["muted"]};}}
    </style><div class="fs-word-cloud" role="list" aria-label="Authored headline word frequencies">''' + ''.join(words) + '</div>'
