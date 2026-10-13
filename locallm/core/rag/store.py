"""SQLite persistence and incremental vector/lexical index store for workspaces."""

import json
import math
from pathlib import Path
import sqlite3
import struct
import time
from typing import Any, Dict, List, Optional, Tuple
from locallm.core.rag.bm25 import BM25Scorer
from locallm.core.rag.chunker import DocumentChunk, chunk_document


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two float vectors in pure Python."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class KnowledgeStore:
    """Persistent local SQLite knowledge index for a specific workspace."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.db_path = workspace_path / "knowledge_index.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database tables and indexes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS indexed_files (
                    file_path TEXT PRIMARY KEY,
                    rel_path TEXT,
                    mtime REAL,
                    size INTEGER,
                    chunk_count INTEGER,
                    indexed_at REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    file_path TEXT,
                    rel_path TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    section_title TEXT,
                    content TEXT,
                    token_count INTEGER,
                    embedding BLOB
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_rel ON chunks(rel_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_path)")

    def sync_workspace_knowledge(
        self,
        ollama_host: str = "http://127.0.0.1:11434",
        embedding_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Scan workspace knowledge/ directory and perform incremental indexing."""
        knowledge_dir = self.workspace_path / "knowledge"
        if not knowledge_dir.exists():
            knowledge_dir.mkdir(parents=True, exist_ok=True)

        supported_suffixes = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".csv", ".sh", ".sql"}
        disk_files: Dict[str, Path] = {}
        for f in knowledge_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in supported_suffixes:
                disk_files[str(f.resolve())] = f

        added_files = 0
        updated_files = 0
        deleted_files = 0
        total_chunks = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path, mtime, size FROM indexed_files")
            cached_files = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

            # 1. Prune removed files
            for cached_path in list(cached_files.keys()):
                if cached_path not in disk_files:
                    cursor.execute("DELETE FROM indexed_files WHERE file_path = ?", (cached_path,))
                    cursor.execute("DELETE FROM chunks WHERE file_path = ?", (cached_path,))
                    deleted_files += 1

            # 2. Process modified or new files
            for abs_path_str, file_obj in disk_files.items():
                stat = file_obj.stat()
                mtime = stat.st_mtime
                size = stat.st_size

                cached_stat = cached_files.get(abs_path_str)
                if cached_stat and cached_stat[0] == mtime and cached_stat[1] == size:
                    # File unchanged
                    continue

                is_update = abs_path_str in cached_files
                try:
                    rel_name = str(file_obj.relative_to(knowledge_dir)).replace("\\", "/")
                    text = file_obj.read_text(encoding="utf-8", errors="replace")
                    file_chunks = chunk_document(text, abs_path_str, rel_name)

                    # Remove old chunks for this file
                    cursor.execute("DELETE FROM chunks WHERE file_path = ?", (abs_path_str,))

                    for c in file_chunks:
                        cursor.execute(
                            """
                            INSERT INTO chunks (
                                chunk_id, file_path, rel_path, start_line, end_line,
                                section_title, content, token_count, embedding
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                c.chunk_id,
                                c.file_path,
                                c.rel_path,
                                c.start_line,
                                c.end_line,
                                c.section_title,
                                c.content,
                                c.token_count,
                                None,
                            ),
                        )

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO indexed_files (
                            file_path, rel_path, mtime, size, chunk_count, indexed_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (abs_path_str, rel_name, mtime, size, len(file_chunks), time.time()),
                    )

                    if is_update:
                        updated_files += 1
                    else:
                        added_files += 1
                except Exception:
                    continue

            conn.commit()
            cursor.execute("SELECT COUNT(*) FROM chunks")
            total_chunks = cursor.fetchone()[0]

        return {
            "workspace": self.workspace_path.name,
            "added_files": added_files,
            "updated_files": updated_files,
            "deleted_files": deleted_files,
            "total_chunks": total_chunks,
        }

    def get_all_chunks(self) -> List[DocumentChunk]:
        """Fetch all indexed document chunks from SQLite store."""
        chunks: List[DocumentChunk] = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT chunk_id, file_path, rel_path, start_line, end_line,
                       section_title, content, token_count
                FROM chunks
                """
            )
            for row in cursor.fetchall():
                chunks.append(
                    DocumentChunk(
                        chunk_id=row[0],
                        file_path=row[1],
                        rel_path=row[2],
                        start_line=row[3],
                        end_line=row[4],
                        section_title=row[5],
                        content=row[6],
                        token_count=row[7],
                    )
                )
        return chunks

    def search(self, query: str, top_k: int = 5) -> List[Tuple[DocumentChunk, float]]:
        """Perform semantic and BM25 hybrid search over indexed document chunks."""
        chunks = self.get_all_chunks()
        if not chunks or not query.strip():
            return []

        scorer = BM25Scorer()
        scorer.fit(chunks)
        ranked = scorer.rank(query, chunks, top_k=top_k)
        return ranked
