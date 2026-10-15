import re
import os
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from config import settings

logger = logging.getLogger("qdrant_service")

# Regex patterns to sanitize sensitive tokens before saving
SENSITIVE_PATTERNS = [
    r"(?i)(api[_-]?key|secret|token|password|auth|bearer)\s*[:=]\s*['\"]([^'\"]+)['\"]",
    r"gsk_[a-zA-Z0-9]{20,}",
    r"sk-[a-zA-Z0-9]{20,}",
    r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}",
]

def sanitize_code_and_text(text: str) -> str:
    """Removes API keys, passwords, and secrets from code/text before vector storage."""
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, "[REDACTED_SECRET]", sanitized)
    return sanitized

class QdrantService:
    def __init__(self, vector_size: int = 384):
        self.vector_size = vector_size
        self.collection_name = settings.qdrant_collection
        self.client = self._init_client()
        self._ensure_collection()

    def _init_client(self) -> QdrantClient:
        if settings.qdrant_url and settings.qdrant_url.strip():
            logger.info(f"Connecting to remote/docker Qdrant at: {settings.qdrant_url}")
            return QdrantClient(
                url=settings.qdrant_url.strip(),
                api_key=settings.qdrant_api_key.strip() if settings.qdrant_api_key else None,
                timeout=10.0,
            )
        else:
            storage_path = str(settings.storage_dir)
            os.makedirs(storage_path, exist_ok=True)
            logger.info(f"Using local embedded Qdrant storage at: {storage_path}")
            return QdrantClient(path=storage_path)

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )
        except Exception as e:
            logger.warning(f"Collection check or creation notice: {e}")

    def upsert_points(self, points: List[PointStruct]) -> bool:
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert points into Qdrant: {e}")
            return False

    def search_similar(self, query_vector: List[float], limit: int = 4, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        try:
            # Qdrant modern query_points API
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                score_threshold=score_threshold if score_threshold > 0 else None,
            )
            hits = []
            for hit in results.points:
                payload = hit.payload or {}
                hits.append({
                    "id": str(hit.id),
                    "score": round(float(hit.score), 4) if getattr(hit, "score", None) is not None else 1.0,
                    "error_type": payload.get("error_type", "Unknown"),
                    "title": payload.get("title", ""),
                    "root_cause": payload.get("root_cause", ""),
                    "buggy_code": payload.get("buggy_code", ""),
                    "corrected_code": payload.get("corrected_code", ""),
                    "test_code": payload.get("test_code", ""),
                    "category": payload.get("category", ""),
                    "tags": payload.get("tags", []),
                    "source": payload.get("source", "knowledge_base"),
                    "snippet": payload.get("text", payload.get("root_cause", "")),
                })
            return hits
        except Exception as e:
            logger.error(f"Error during Qdrant search: {e}")
            return []

    def count(self) -> int:
        try:
            res = self.client.count(collection_name=self.collection_name, exact=True)
            return res.count
        except Exception as e:
            logger.warning(f"Failed to get collection count: {e}")
            return 0

    def get_all_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            records, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            results = []
            for r in records:
                payload = r.payload or {}
                results.append({
                    "id": str(r.id),
                    **payload
                })
            return results
        except Exception as e:
            logger.error(f"Failed to scroll records: {e}")
            return []

qdrant_service = QdrantService()
