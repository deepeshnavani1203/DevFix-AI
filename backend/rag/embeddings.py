import logging
import hashlib
from typing import List
from config import settings

logger = logging.getLogger("embeddings")

class EmbeddingModel:
    def __init__(self):
        self.model_name = settings.embedding_model
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer ({e}). Using deterministic vector fallback.")
                self._model = None
        return self._model

    def encode(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self.model is not None:
            try:
                embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                return embeddings.tolist()
            except Exception as e:
                logger.error(f"Encoding failed with SentenceTransformer: {e}")

        # Deterministic 384-dimensional fallback embeddings
        return [self._fallback_embedding(t) for t in texts]

    def encode_one(self, text: str) -> List[float]:
        return self.encode([text])[0]

    def _fallback_embedding(self, text: str) -> List[float]:
        """Generates a normalized 384-dim pseudo-semantic vector using hashed token buckets."""
        vec = [0.0] * 384
        tokens = text.lower().split()
        for token in tokens:
            token_hash = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
            idx = token_hash % 384
            vec[idx] += 1.0
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

embedding_model = EmbeddingModel()
