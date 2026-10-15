import os
from pathlib import Path
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

# Load .env from backend directory
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

MODEL_ALIASES = {
    "gpt-oss-120b": "openai/gpt-oss-120b",
    "gpt-oss-20b": "openai/gpt-oss-20b",
    "qwen3.8-27b": "qwen/qwen3.8-27b",
    "llama-3.3-70b": "llama-3.3-70b-versatile",
}

class Settings(BaseModel):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    qdrant_url: str = os.getenv("QDRANT_URL", "")
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "devfix_knowledge")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    storage_dir: Path = BASE_DIR / "qdrant_storage"

    @field_validator("groq_model")
    @classmethod
    def normalize_model(cls, v: str) -> str:
        clean = v.strip()
        return MODEL_ALIASES.get(clean, clean)

settings = Settings()
