"""Workspace knowledge search and indexing tools for locaLLM."""

from typing import Any, Dict, Optional
from locallm.core.rag.engine import get_rag_engine
from locallm.core.tools.base import tool


def search_knowledge_fn(
    query: str,
    top_k: int = 5,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Search workspace knowledge base documents using BM25 and vector ranking."""
    q = query.strip()
    if not q:
        return "Error: Search query cannot be empty."

    ws_name = (context or {}).get("workspace_name")
    engine = get_rag_engine()
    return engine.search(query=q, workspace_name=ws_name, top_k=int(top_k or 5))


def index_knowledge_fn(
    workspace: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Synchronize and re-index workspace knowledge base files into SQLite store."""
    ws_name = workspace or (context or {}).get("workspace_name")
    engine = get_rag_engine()
    result = engine.index_workspace(workspace_name=ws_name)
    target_ws = result.get("workspace", ws_name or "active")
    added = result.get("added_files", 0)
    updated = result.get("updated_files", 0)
    deleted = result.get("deleted_files", 0)
    total_chunks = result.get("total_chunks", 0)

    return (
        f"Workspace '{target_ws}' knowledge index updated successfully: "
        f"{added} added, {updated} updated, {deleted} removed. "
        f"Total indexed passages: {total_chunks}."
    )


# Register tools
tool(
    name="search_knowledge",
    description="Search workspace knowledge base documents (.md, .txt) using BM25 and vector ranking. Returns relevant passages with line numbers and file paths.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query, topic, keyword, or question to search in workspace knowledge files.",
            },
            "top_k": {
                "type": "integer",
                "description": "Maximum number of ranked passages to return (default: 5).",
            },
        },
        "required": ["query"],
    },
    is_mutating=False,
    is_privileged=False,
    categories={"assistant", "telegram", "whatsapp"},
)(search_knowledge_fn)

tool(
    name="index_knowledge",
    description="Synchronize and re-index workspace knowledge base files into the vector and BM25 index.",
    parameters={
        "type": "object",
        "properties": {
            "workspace": {
                "type": "string",
                "description": "Optional workspace name to index. If omitted, uses active workspace.",
            },
        },
    },
    is_mutating=True,
    is_privileged=False,
    categories={"assistant", "telegram", "whatsapp"},
)(index_knowledge_fn)
