import uuid
from typing import List, Dict, Any

def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
    metadata: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """Chunks a block of text or markdown into overlapping segments with metadata."""
    if metadata is None:
        metadata = {}
    
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_str = " ".join(chunk_words)

        chunks.append({
            "id": str(uuid.uuid4()),
            "text": chunk_str,
            "metadata": {
                **metadata,
                "word_count": len(chunk_words),
                "chunk_index": len(chunks),
            }
        })
        if end >= len(words):
            break
        start += (chunk_size - overlap)
    
    return chunks

def prepare_knowledge_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares a single Python error knowledge record into a searchable document format."""
    text_representation = f"""Error Type: {item.get('error_type', '')}
Title: {item.get('title', '')}
Root Cause: {item.get('root_cause', '')}
Buggy Code Example:
{item.get('buggy_code', '')}
Corrected Code:
{item.get('corrected_code', '')}
Tags: {', '.join(item.get('tags', []))}
Category: {item.get('category', '')}
"""
    return {
        "id": item.get("id"),
        "text": text_representation.strip(),
        "metadata": {
            "error_type": item.get("error_type", ""),
            "title": item.get("title", ""),
            "root_cause": item.get("root_cause", ""),
            "buggy_code": item.get("buggy_code", ""),
            "corrected_code": item.get("corrected_code", ""),
            "test_code": item.get("test_code", ""),
            "category": item.get("category", ""),
            "tags": item.get("tags", []),
            "source": item.get("source", "verified_knowledge_base"),
            "language": item.get("language", "python")
        }
    }
