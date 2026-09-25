"""Formats a list of retrieved items (from vector_search_tool or sql_query_tool)
into a consistent, numbered citation block agents can append to an answer."""

def citation_formatter_tool(items: list, style: str = "inline"):
    """items: list of dicts, each with at least an 'id' (or 'doc_id'/'trial_id') and a
    'label' describing it. style: 'inline' -> [1] [2]..., 'list' -> a reference list."""
    entries = []
    for i, it in enumerate(items, start=1):
        ref_id = it.get("id") or it.get("doc_id") or it.get("trial_id") or f"item-{i}"
        label = it.get("label") or it.get("title") or ref_id
        entries.append({"n": i, "id": ref_id, "label": label})

    if style == "inline":
        text = " ".join(f"[{e['id']}]" for e in entries)
    else:
        text = "\n".join(f"[{e['n']}] {e['id']} - {e['label']}" for e in entries)
    return {"entries": entries, "formatted": text}