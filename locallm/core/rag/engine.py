"""Unified RAG coordinator and knowledge retrieval engine for locaLLM workspaces."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from locallm.config import load_config
from locallm.core.rag.store import KnowledgeStore
from locallm.core.workspace import get_workspace_path


class RAGEngine:
    """High-level knowledge indexing and passage retrieval engine."""

    def __init__(self):
        self._stores: Dict[str, KnowledgeStore] = {}

    def _get_store(self, workspace_name: str) -> KnowledgeStore:
        """Resolve or cache KnowledgeStore for a specific workspace."""
        clean_name = workspace_name.strip() if workspace_name else "default"
        if clean_name not in self._stores:
            ws_dir = get_workspace_path(clean_name)
            self._stores[clean_name] = KnowledgeStore(ws_dir)
        return self._stores[clean_name]

    def index_workspace(self, workspace_name: Optional[str] = None) -> Dict[str, Any]:
        """Perform incremental indexing of workspace knowledge directory."""
        cfg = load_config()
        ws_name = workspace_name or getattr(cfg, "active_workspace", "default")
        store = self._get_store(ws_name)
        result = store.sync_workspace_knowledge(
            ollama_host=getattr(cfg, "ollama_host", "http://127.0.0.1:11434"),
        )
        return result

    def search(
        self,
        query: str,
        workspace_name: Optional[str] = None,
        top_k: int = 5,
    ) -> str:
        """Search workspace knowledge documents and format relevant passages for the AI."""
        if not query.strip():
            return "Error: Search query cannot be empty."

        cfg = load_config()
        ws_name = workspace_name or getattr(cfg, "active_workspace", "default")
        store = self._get_store(ws_name)

        # Ensure documents are synced incrementally
        store.sync_workspace_knowledge(
            ollama_host=getattr(cfg, "ollama_host", "http://127.0.0.1:11434"),
        )

        ranked = store.search(query, top_k=top_k)
        if not ranked:
            return f"No relevant knowledge passages found in workspace '{ws_name}' matching query '{query}'."

        formatted_passages: List[str] = [
            f"Found {len(ranked)} relevant knowledge passages in workspace '{ws_name}':\n"
        ]

        for idx, (chunk, score) in enumerate(ranked, start=1):
            title = chunk.section_title or "General"
            line_info = f"Lines {chunk.start_line}-{chunk.end_line}"
            formatted_passages.append(
                f"[Passage {idx}: {chunk.rel_path} ({line_info}) | Section: {title} | Relevance: {score:.2f}]\n"
                f"{chunk.content}\n"
            )

        return "\n".join(formatted_passages)

    def get_knowledge_summary(self, workspace_name: Optional[str] = None) -> str:
        """Generate a concise index summary of indexed files in the workspace."""
        cfg = load_config()
        ws_name = workspace_name or getattr(cfg, "active_workspace", "default")
        store = self._get_store(ws_name)
        chunks = store.get_all_chunks()
        if not chunks:
            return ""

        file_map: Dict[str, List[str]] = {}
        for c in chunks:
            if c.rel_path not in file_map:
                file_map[c.rel_path] = []
            if c.section_title and c.section_title not in file_map[c.rel_path]:
                file_map[c.rel_path].append(c.section_title)

        summary_lines = [
            f"[Workspace Knowledge Base Index: {len(file_map)} files, {len(chunks)} passages]",
            "Indexed documentation available for semantic search via 'search_knowledge(query=...)':"
        ]
        for f_name, sections in sorted(file_map.items()):
            topics_str = f" (Topics: {', '.join(sections[:4])})" if sections else ""
            summary_lines.append(f"- {f_name}{topics_str}")

        return "\n".join(summary_lines)


_global_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Return singleton instance of RAGEngine."""
    global _global_rag_engine
    if _global_rag_engine is None:
        _global_rag_engine = RAGEngine()
    return _global_rag_engine
