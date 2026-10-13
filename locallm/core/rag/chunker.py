"""Document chunking and structural section parser for RAG indexing."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List


@dataclass
class DocumentChunk:
    """Passage chunk extracted from a workspace document."""

    chunk_id: str
    file_path: str
    rel_path: str
    start_line: int
    end_line: int
    section_title: str
    content: str
    token_count: int


def _split_into_paragraphs(text: str) -> List[tuple[str, int, int]]:
    """Split text into blocks keeping line number ranges."""
    lines = text.splitlines(keepends=True)
    if not lines:
        return []

    blocks: List[tuple[str, int, int]] = []
    current_lines: List[str] = []
    current_start = 1

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        # Markdown header triggers immediate block boundary
        if stripped.startswith("#") and current_lines:
            block_text = "".join(current_lines)
            blocks.append((block_text, current_start, idx - 1))
            current_lines = [line]
            current_start = idx
        elif not stripped and current_lines:
            current_lines.append(line)
            block_text = "".join(current_lines)
            blocks.append((block_text, current_start, idx))
            current_lines = []
            current_start = idx + 1
        else:
            current_lines.append(line)

    if current_lines:
        block_text = "".join(current_lines)
        blocks.append((block_text, current_start, len(lines)))

    return blocks


def chunk_document(
    text: str,
    file_path: str,
    rel_path: str,
    target_chunk_size: int = 1000,
    overlap_size: int = 150,
) -> List[DocumentChunk]:
    """Chunk a document into overlapping passages with line numbers and section titles."""
    if not text.strip():
        return []

    blocks = _split_into_paragraphs(text)
    if not blocks:
        return []

    chunks: List[DocumentChunk] = []
    current_title = Path(rel_path).stem.replace("_", " ").title()

    accumulated_text = ""
    chunk_start_line = 1
    chunk_end_line = 1
    chunk_counter = 0

    for block_text, b_start, b_end in blocks:
        # Detect section header
        header_match = re.search(r"^(#{1,6}\s+.+)", block_text, re.MULTILINE)
        new_header = header_match.group(1).lstrip("#").strip() if header_match else None

        # If a new section header is encountered and we have accumulated meaningful content, flush previous chunk
        if new_header and accumulated_text.strip() and len(accumulated_text.strip()) >= 50:
            chunk_counter += 1
            c_id = f"{rel_path}:{chunk_counter}"
            chunks.append(
                DocumentChunk(
                    chunk_id=c_id,
                    file_path=file_path,
                    rel_path=rel_path,
                    start_line=chunk_start_line,
                    end_line=chunk_end_line,
                    section_title=current_title,
                    content=accumulated_text.strip(),
                    token_count=len(accumulated_text.split()),
                )
            )
            accumulated_text = ""
            current_title = new_header
            chunk_start_line = b_start
        elif new_header:
            current_title = new_header

        if not accumulated_text:
            chunk_start_line = b_start

        candidate_len = len(accumulated_text) + len(block_text)
        if candidate_len <= target_chunk_size:
            accumulated_text += block_text
            chunk_end_line = b_end
        else:
            if accumulated_text.strip():
                chunk_counter += 1
                c_id = f"{rel_path}:{chunk_counter}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=c_id,
                        file_path=file_path,
                        rel_path=rel_path,
                        start_line=chunk_start_line,
                        end_line=chunk_end_line,
                        section_title=current_title,
                        content=accumulated_text.strip(),
                        token_count=len(accumulated_text.split()),
                    )
                )

            if overlap_size > 0 and len(accumulated_text) > overlap_size:
                overlap_text = accumulated_text[-overlap_size:]
                accumulated_text = overlap_text + block_text
            else:
                accumulated_text = block_text
            chunk_start_line = b_start
            chunk_end_line = b_end

    if accumulated_text.strip():
        chunk_counter += 1
        c_id = f"{rel_path}:{chunk_counter}"
        chunks.append(
            DocumentChunk(
                chunk_id=c_id,
                file_path=file_path,
                rel_path=rel_path,
                start_line=chunk_start_line,
                end_line=chunk_end_line,
                section_title=current_title,
                content=accumulated_text.strip(),
                token_count=len(accumulated_text.split()),
            )
        )

    return chunks
