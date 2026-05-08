"""
services/summarization_service.py — Document summarization logic.
"""
from app.services.openai_service import openai_service
from app.vectorstore.faiss_store import faiss_store
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Prompt templates based on summary type
_PROMPTS = {
    "brief": "You are a helpful AI. Provide a very concise, 2-3 sentence brief summary of the following document. Preserve the most important insight.",
    "detailed": "You are an expert analyst. Provide a detailed, comprehensive summary of the following document. Include key topics, important insights, and preserve the nuance of the text. Avoid hallucinating information not present in the text.",
    "bullet points": "You are a helpful AI. Summarize the key points of the following document as a concise bulleted list. Ensure the most important insights are preserved. Avoid hallucinating."
}

class SummarizationService:
    async def summarize(self, filename: str, summary_type: str = "detailed") -> str:
        """
        Retrieve chunks for a file, intelligently combine them to avoid token limits,
        and generate a summary.
        """
        if summary_type not in _PROMPTS:
            summary_type = "detailed"
            
        system_prompt = _PROMPTS[summary_type]
        
        # 1. Retrieve chunks
        chunks = faiss_store.get_document_text(filename)
        if not chunks:
            raise ValueError(f"No document found with filename: {filename}")
            
        # 2. Combine chunks intelligently (Simple strategy for token limits)
        # Assuming ~4 characters per token, and GPT-4o has a large context window (128k).
        # We can combine up to 100k chars safely. If it exceeds, we truncate for this simple version.
        # A more advanced strategy would be Map-Reduce (summarize chunks, then summarize the summaries).
        combined_text = "\n".join(chunks)
        max_chars = 100000 
        
        if len(combined_text) > max_chars:
            logger.warning("Document %s is very large (%d chars). Truncating for summarization.", filename, len(combined_text))
            combined_text = combined_text[:max_chars]
            
        # 3. Generate summary
        logger.info("Generating %s summary for %s (%d chunks)", summary_type, filename, len(chunks))
        
        user_message = f"Please summarize the following document:\n\n{combined_text}"
        
        answer = await openai_service.chat(
            user_message=user_message,
            system_prompt=system_prompt
        )
        
        return answer

# Singleton
summarization_service = SummarizationService()
