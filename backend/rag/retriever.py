import logging
from typing import List, Dict, Any
from rag.embeddings import embedding_model
from services.qdrant_service import qdrant_service

logger = logging.getLogger("retriever")

class RAGRetriever:
    def __init__(self, top_k: int = 4):
        self.top_k = top_k

    def retrieve(self, query: str, limit: int = None, score_threshold: float = 0.15) -> List[Dict[str, Any]]:
        k = limit or self.top_k
        if not query.strip():
            return []
        try:
            query_vector = embedding_model.encode_one(query)
            results = qdrant_service.search_similar(
                query_vector=query_vector,
                limit=k,
                score_threshold=score_threshold
            )
            return results
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []

    def retrieve_for_debug_context(self, code: str, error_message: str, error_type: str = "") -> List[Dict[str, Any]]:
        """Constructs an optimized query vector combining error type, message, and problematic code."""
        query_parts = []
        if error_type:
            query_parts.append(f"Error: {error_type}")
        if error_message:
            query_parts.append(f"Traceback: {error_message[:300]}")
        if code:
            query_parts.append(f"Code: {code[:300]}")

        query = "\n".join(query_parts)
        return self.retrieve(query)

rag_retriever = RAGRetriever()
