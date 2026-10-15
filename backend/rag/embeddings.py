import logging
import hashlib
from typing import List
from config import settings

logger = logging.getLogger("embeddings")

class EmbeddingModel:
    def __init__(self):
        self.model_name = settings.embedding_model
        self._model = None
        self._cache: dict = {}

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.model_name}")
                # Try loading from local HuggingFace cache first to avoid slow network roundtrips
                try:
                    self._model = SentenceTransformer(self.model_name, local_files_only=True)
                except Exception:
                    self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer ({e}). Using deterministic vector fallback.")
                self._model = None
        return self._model

    def warm_up(self):
        """Pre-warm model into RAM at application startup."""
        if self.model is not None:
            try:
                self.encode_one("warmup query")
                logger.info("Embedding model pre-warmed successfully.")
            except Exception as e:
                logger.warning(f"Embedding warmup notice: {e}")

    def encode(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        results = []
        uncached_indices = []
        uncached_texts = []

        for idx, text in enumerate(texts):
            clean_t = text.strip()
            if clean_t in self._cache:
                results.append(self._cache[clean_t])
            else:
                results.append(None)
                uncached_indices.append(idx)
                uncached_texts.append(clean_t)

        if uncached_texts:
            new_embeddings = None
            if self.model is not None:
                try:
                    embeddings = self.model.encode(uncached_texts, convert_to_numpy=True, normalize_embeddings=True)
                    new_embeddings = embeddings.tolist()
                except Exception as e:
                    logger.error(f"Encoding failed with SentenceTransformer: {e}")

            if new_embeddings is None:
                new_embeddings = [self._fallback_embedding(t) for t in uncached_texts]

            for orig_idx, emb in zip(uncached_indices, new_embeddings):
                results[orig_idx] = emb
                # Cache up to 1000 items
                if len(self._cache) < 1000:
                    self._cache[texts[orig_idx].strip()] = emb

        return results

    def encode_one(self, text: str) -> List[float]:
        clean_t = text.strip()
        if clean_t in self._cache:
            return self._cache[clean_t]
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
