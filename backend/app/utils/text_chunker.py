"""
utils/text_chunker.py — Text chunking utilities.
"""

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Split text into overlapping chunks by character count.
    
    Args:
        text: The text to chunk.
        chunk_size: Maximum size of each chunk.
        overlap: Number of characters to overlap between chunks.
        
    Returns:
        List of text chunks.
    """
    if not text:
        return []
        
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]

def chunk_transcript(segments: list[dict], chunk_size: int = 1000) -> list[dict]:
    """
    Group Whisper transcript segments into larger semantic chunks.
    Preserves start and end timestamps for each chunk.
    
    Returns a list of dicts:
    [{"text": "...", "start": 0.0, "end": 15.5}, ...]
    """
    chunks = []
    current_text = ""
    current_start = None
    current_end = None
    
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
            
        if current_start is None:
            current_start = seg.get("start")
            
        if len(current_text) + len(text) > chunk_size and current_text:
            chunks.append({
                "text": current_text.strip(),
                "start": current_start,
                "end": current_end
            })
            current_text = text + " "
            current_start = seg.get("start")
            current_end = seg.get("end")
        else:
            current_text += text + " "
            current_end = seg.get("end")
            
    if current_text:
        chunks.append({
            "text": current_text.strip(),
            "start": current_start,
            "end": current_end
        })
        
    return chunks
