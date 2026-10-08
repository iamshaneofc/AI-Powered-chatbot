"""
services/rag_service.py — LangChain-style RAG (Retrieval-Augmented Generation) pipeline.

Pipeline:
  1. Embed the question          (OpenAI Embeddings)
  2. Retrieve top-k chunks       (FAISS vector search)
  3. Build a grounded prompt     (context + question)
  4. Generate an answer          (OpenAI GPT)

Usage:
    from app.services.rag_service import rag_service

    result = await rag_service.answer("What is the document about?", top_k=5)
    print(result["answer"])
    print(result["sources"])
"""

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────
_RAG_SYSTEM_PROMPT = """You are Novara AI, a highly intelligent, conversational, and helpful assistant. 
Your primary purpose is to answer user questions based on the provided document or media context.

Guidelines:
1. Be friendly, natural, and conversational in your tone. Avoid robotic phrasing.
2. If the user's query is conversational (e.g., greetings, general chat), respond politely but gently remind them that your main capability is analyzing their uploaded documents.
3. If the provided context contains the answer, explain it clearly and naturally.
4. If the provided context is only partially related, provide a contextual answer based on what IS available, summarizing nearby relevant concepts instead of just giving up.
5. If the provided context is completely unrelated to the user's query, politely explain that you cannot find the specific information in the uploaded documents. Avoid rigid, repetitive phrases like "I don't have enough information." Instead, explain your limitations naturally and tell them what the provided documents are actually about.
6. Do NOT hallucinate facts outside the provided context when answering specific factual questions about the documents.

Your goal is to feel like a polished, intelligent AI assistant rather than a strict keyword-based retrieval bot."""


class RAGService:
    """
    Retrieval-Augmented Generation pipeline.

    Deliberately kept simple and dependency-light so it's easy to
    swap the retriever or LLM backend later.
    """

    async def answer(
        self, 
        question: str, 
        top_k: int | None = None, 
        filename_filter: str | None = None,
        session_id: str | None = None
    ) -> dict:
        """
        Run the full RAG pipeline.

        Args:
            question:        The user's natural-language question.
            top_k:           Number of context chunks to retrieve.
            filename_filter: Optional source file to limit search to.
            session_id:      Optional session ID to retrieve chat history.

        Returns:
            {
                "answer":  str,           # GPT's grounded answer
                "sources": list[str],     # source filenames / identifiers
                "model":   str,           # model used
                "chunks":  list[dict],    # raw retrieved chunks (debug)
            }
        """
        top_k = top_k or settings.VECTOR_TOP_K

        from app.services.vector_service import vector_service
        from app.services.openai_service  import openai_service
        from app.services.redis_service import redis_service

        # ── Step 0: Lightweight Intent Classification ────────────────────
        casual_greetings = {
            "hi", "hello", "hey", "how are you", "how are you doing", "what can you do",
            "what do you do", "thanks", "thank you", "morning", "good morning",
            "good evening", "sup", "hi there", "hello there"
        }
        clean_q = question.lower().strip().strip('?!.,')
        
        if clean_q in casual_greetings:
            return {
                "answer": "Hello! I'm Novara AI. I specialize in analyzing and answering questions about your uploaded documents and media. Feel free to upload a file to get started, or ask me about something you've already uploaded!",
                "sources": [],
                "model": settings.get_active_model(),
                "chunks": [],
            }

        # ── Step 1: Retrieve conversation history ────────────────────────
        history_context = ""
        if session_id:
            history = await redis_service.get_history(session_id, limit=5)
            if history:
                # Reverse history to be chronological for the prompt
                history_parts = []
                for entry in reversed(history):
                    history_parts.append(f"User: {entry['question']}\nAssistant: {entry['answer']}")
                history_context = "\n\nPrevious conversation:\n" + "\n".join(history_parts)

        # ── Step 2: Retrieve relevant chunks ─────────────────────────────
        # If there's history, we could optionally use it to rephrase the query,
        # but for now, we just search with the current question.
        chunks = await vector_service.search(question, top_k=top_k, filename_filter=filename_filter)

        if not chunks:
            logger.warning("No chunks retrieved for question: %s", question[:80])
            return {
                "answer": "I don't have any uploaded documents that match your request right now. I specialize in analyzing the files you provide—please upload some documents or media, and I'd be happy to help!",
                "sources": [],
                "model": settings.get_active_model(),
                "chunks": [],
            }

        # ── Step 3: Build context string ──────────────────────────────────
        context_parts = []
        sources: list[str] = []

        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("metadata", {}).get("source", "unknown")
            if source not in sources:
                sources.append(source)
            context_parts.append(f"[{i}] (source: {source})\n{chunk['text']}")

        context = "\n\n".join(context_parts)
        
        # Prepend history if available
        if history_context:
            context = history_context + "\n\n" + "Current relevant document context:\n" + context

        # ── Step 4: Generate grounded answer ─────────────────────────────
        logger.info(
            "RAG: retrieved %d chunks from %d sources (session=%s) → sending to GPT",
            len(chunks), len(sources), session_id
        )

        answer = await openai_service.chat(
            user_message=question,
            system_prompt=_RAG_SYSTEM_PROMPT,
            context=context,
        )

        return {
            "answer":  answer,
            "sources": sources,
            "model":   settings.get_active_model(),
            "chunks":  chunks,
        }

    async def answer_with_langchain(self, question: str, top_k: int | None = None) -> dict:
        """
        Alternative implementation using the full LangChain LCEL pipeline.

        Requires: pip install langchain langchain-openai langchain-community
        Swap `answer` → `answer_with_langchain` in query.py to activate.
        """
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from langchain_community.vectorstores import FAISS as LangFAISS
        from langchain.chains import RetrievalQA
        from langchain.prompts import PromptTemplate

        from app.vectorstore.faiss_store import faiss_store

        # Re-use existing FAISS index via LangChain wrapper
        lc_faiss = LangFAISS(
            embedding_function=OpenAIEmbeddings(
                model=settings.get_active_embedding_model(),
                openai_api_key=settings.get_active_api_key(),
                base_url=settings.get_active_base_url(),
            ),
            index=faiss_store.index,
            docstore=faiss_store.docstore,
            index_to_docstore_id=faiss_store.index_to_docstore_id,
        )

        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template=(
                "Use the following context to answer the question.\n\n"
                "Context:\n{context}\n\n"
                "Question: {question}\n\n"
                "Answer:"
            ),
        )

        llm = ChatOpenAI(
            model=settings.get_active_model(),
            temperature=settings.OPENAI_TEMPERATURE,
            openai_api_key=settings.get_active_api_key(),
            base_url=settings.get_active_base_url(),
        )

        chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=lc_faiss.as_retriever(search_kwargs={"k": top_k or settings.VECTOR_TOP_K}),
            chain_type_kwargs={"prompt": prompt_template},
            return_source_documents=True,
        )

        result = await chain.ainvoke({"query": question})

        sources = list({doc.metadata.get("source", "unknown") for doc in result["source_documents"]})
        return {
            "answer":  result["result"],
            "sources": sources,
            "model":   settings.get_active_model(),
            "chunks":  [],
        }


# Singleton
rag_service = RAGService()
