"""Reviewed local-product copy and authored context; no local runtime imports."""

LOCAL_REVIEW_SHA = "7e6c5158c56ac0a520119f91ddfbb2fae9041782"
LOCAL_REVIEW_DATE = "3 November 2026"
ALL_PARENTS = "All topic parents"
ALL_CHILDREN = "All child topics"
UNCLASSIFIED = "Unclassified"

GUIDE_STEPS = (
    ("sources", "Settings", "Choose sources, permissions, current budgets and analysis models."),
    ("analyze", "Update & Analyze", "Submit one explicit local task from your saved configuration."),
    ("model", "Background Worker", "Collect → classify → sentiment → save. Checkpoints retain progress."),
    ("inspect", "Dashboard", "Inspect Industries, Graph and News Explorer with shared local filters."),
)
CAPABILITIES = (
    ("sources", "News collection", "Implemented", "Broad financial news · Selected media · Company tracking",
     "Configured sources, permitted fields and current budgets. NewsData remains paused."),
    ("analyze", "Background processing", "Implemented", "Persistent local tasks, separate from the UI",
     "Saved stages, resource pauses and explicit continuation through the local worker."),
    ("model", "Model selection", "Defaults + optional", "FinBERT sentiment + MiniLM embeddings",
     "LM Studio / Ollama: configured integrations. DeepSeek: limited authored-text interface test."),
    ("inspect", "Sector intelligence", "Implemented", "Parent / child topics and shared local filters",
     "Originals, source evidence and model history. Company metadata stays separate from text topics."),
)
SOURCE_CARDS = (
    ("News APIs", "Marketaux and Finnhub need configured accounts, source scope and a current budget. NewsData remains manually paused, including paid-content access."),
    ("Official and regulatory sources", "Reviewed ABS, NIST, RBA and SEC adapters have bounded routes and source-specific policies. SEC requires your actual contact identity. ACCC remains disabled."),
    ("Local imports", "Strict JSONL/CSV imports accept approved inputs with their provenance and rights. Finite private-research file imports remain restricted."),
    ("Media-link discovery", "Five fixed Bloomberg, CNBC, WSJ, FT and Yahoo feeds support separate link discovery. Opt-in monitoring needs a dated budget; link counts are not licensed-text or NLP counts."),
)
MODEL_CARDS = (
    ("Local defaults", "Pinned FinBERT supplies sentiment; MiniLM supplies embeddings and topic-candidate recall. Sentiment is text tone, not a return forecast."),
    ("Independent industry topics", "The topic scheme and configured local classifier are separate from sentiment selection. Company metadata and collection cohorts do not establish a text topic; retrieval scores are not calibrated confidence."),
    ("Configured alternatives", "LM Studio and Ollama use installed local models and resource checks. Optional external API actions need permitted inputs and explicit send consent; their output provenance stays separate."),
)

# A small authored illustration, not the product taxonomy or model output.
# Every phrase occurs in the original fictional title/summary. Unannotated
# reports stay Unclassified regardless of their company metadata.
AUTHORED_TOPICS = {
    "SYN-001": ("Technology", "Semiconductors", "chip"),
    "SYN-010": ("Financial services", "Savings products", "savings"),
    "SYN-012": ("Financial services", "Digital banking", "bank introduces"),
    "SYN-019": ("Materials", "Recycling", "recycling"),
    "SYN-021": ("Consumer", "Retail operations", "retail format"),
    "SYN-022": ("Consumer", "Retail operations", "store operations"),
    "SYN-023": ("Industrials", "Logistics", "logistics"),
}


def topic_context(row):
    annotation = AUTHORED_TOPICS.get(row.article_id)
    text = (row.title + " " + row.summary).casefold()
    if annotation and annotation[2] in text:
        parent, child, evidence = annotation
        return {"parent": parent, "child": child, "evidence": evidence,
                "status": "Authored illustration"}
    return {"parent": UNCLASSIFIED, "child": None, "evidence": None,
            "status": UNCLASSIFIED}


def topic_select(rows, parent=ALL_PARENTS, child=ALL_CHILDREN):
    return [r for r in rows
            if (parent == ALL_PARENTS or topic_context(r)["parent"] == parent)
            and (child == ALL_CHILDREN or topic_context(r)["child"] == child)]


def topic_rollup(rows):
    """Each authored original contributes once to its parent and child branch."""
    groups = {}
    for row in rows:
        topic = topic_context(row)
        group = groups.setdefault(topic["parent"], {"parent": topic["parent"], "count": 0, "children": {}})
        group["count"] += 1
        child = topic["child"] or "No child label"
        group["children"][child] = group["children"].get(child, 0) + 1
    return [groups[name] for name in sorted(groups, key=lambda name: (name == UNCLASSIFIED, name))]
