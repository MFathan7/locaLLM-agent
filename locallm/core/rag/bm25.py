"""BM25 ranking and lexical scoring engine for local document retrieval."""

import math
import re
from typing import Dict, List, Set, Tuple
from locallm.core.rag.chunker import DocumentChunk

STOPWORDS: Set[str] = {
    # English common stopwords
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "did", "do", "does", "doing", "don", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me",
    "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only",
    "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she", "should",
    "so", "some", "such", "t", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "will", "with", "you", "your", "yours", "yourself", "yourselves",
    # Indonesian common stopwords
    "ada", "adalah", "adanya", "agar", "akan", "akankah", "akhir", "akhiri", "akhirnya", "aku",
    "anda", "antara", "apa", "apabila", "apakah", "apalagi", "atau", "bagaimana", "bagi", "bahkan",
    "bahwa", "baik", "banyak", "batu", "beberapa", "begini", "begitu", "belum", "bila", "bisa",
    "dan", "dapat", "dari", "daripada", "dekat", "dengan", "di", "dia", "dimana", "diri", "ia",
    "ialah", "ibu", "ini", "itu", "jika", "juga", "kalau", "kalian", "kami", "kamu", "karena",
    "ke", "kemudian", "kepada", "kita", "lagi", "lain", "lalu", "lebih", "maka", "mana", "mereka",
    "namun", "oleh", "pada", "para", "per", "pernah", "saat", "saja", "sama", "sampai", "saya",
    "sebab", "sebagai", "sebuah", "secara", "sedang", "sedangkan", "sehingga", "selain", "selama",
    "seluruh", "semakin", "sementara", "semua", "sendiri", "seperti", "serta", "sesuatu", "sesudah",
    "setelah", "setiap", "siapa", "sudah", "supaya", "tapi", "tanpa", "tentang", "tentu", "terhadap",
    "tetapi", "tidak", "untuk", "waduh", "yaitu", "yang"
}


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric keywords with code identifier expansion."""
    if not text:
        return []

    # Expand camelCase and snake_case identifiers
    clean = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    clean = clean.replace("_", " ").replace("-", " ")

    # Extract words
    words = re.findall(r"\b[A-Za-z0-9_]{2,}\b", clean.lower())
    return [w for w in words if w not in STOPWORDS]


class BM25Scorer:
    """Best Matching 25 (BM25Okapi) ranking engine for document passages."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_count = 0
        self.avgdl = 0.0
        self.doc_lengths: Dict[str, int] = {}
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}

    def fit(self, chunks: List[DocumentChunk]) -> None:
        """Build term frequency and inverse document frequency index from chunks."""
        self.doc_count = len(chunks)
        if self.doc_count == 0:
            return

        total_length = 0
        self.doc_freqs.clear()
        self.doc_lengths.clear()

        for chunk in chunks:
            tokens = tokenize(chunk.content)
            dl = len(tokens)
            self.doc_lengths[chunk.chunk_id] = dl
            total_length += dl

            unique_terms = set(tokens)
            for term in unique_terms:
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        self.avgdl = (total_length / self.doc_count) if self.doc_count > 0 else 0.0

        # Calculate standard Lucene/Robertson IDF
        self.idf.clear()
        for term, df in self.doc_freqs.items():
            # Smoothing with +0.5
            val = math.log(1.0 + (self.doc_count - df + 0.5) / (df + 0.5))
            self.idf[term] = max(0.05, val)

    def score(self, query_tokens: List[str], chunk: DocumentChunk) -> float:
        """Calculate BM25 relevance score for a single chunk against query tokens."""
        if not query_tokens or self.doc_count == 0:
            return 0.0

        tokens = tokenize(chunk.content)
        if not tokens:
            return 0.0

        dl = self.doc_lengths.get(chunk.chunk_id, len(tokens))
        tf_map: Dict[str, int] = {}
        for t in tokens:
            tf_map[t] = tf_map.get(t, 0) + 1

        score = 0.0
        len_norm = 1.0 - self.b + self.b * (dl / self.avgdl) if self.avgdl > 0 else 1.0

        for q in query_tokens:
            if q not in tf_map:
                continue
            tf = tf_map[q]
            idf = self.idf.get(q, 0.1)
            # BM25 term weighting formula
            term_score = idf * ((tf * (self.k1 + 1.0)) / (tf + self.k1 * len_norm))
            score += term_score

        # Title bonus: if query term appears in section title or filename
        title_tokens = set(tokenize(f"{chunk.section_title} {chunk.rel_path}"))
        for q in query_tokens:
            if q in title_tokens:
                score += 1.5

        return score

    def rank(
        self,
        query: str,
        chunks: List[DocumentChunk],
        top_k: int = 5,
        min_score: float = 0.2,
    ) -> List[Tuple[DocumentChunk, float]]:
        """Rank chunks by BM25 score against the query."""
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        scored: List[Tuple[DocumentChunk, float]] = []
        for chunk in chunks:
            s = self.score(q_tokens, chunk)
            if s >= min_score:
                scored.append((chunk, s))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]
