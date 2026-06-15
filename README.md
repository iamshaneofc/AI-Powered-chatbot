# AI-Powered Application (Document & Multimedia Q&A)

This project is a full-stack, AI-powered application designed for document processing, multimedia transcription, and intelligent Question & Answering using **Retrieval-Augmented Generation (RAG)**.

## 🚀 Architecture & Tech Stack

This application is built using a decoupled architecture, separating the client-side interface from the heavy AI processing backend.

### **Frontend**
- **Framework:** React 19 + Vite for rapid development and optimized builds.
- **Styling:** Tailwind CSS (v4) for responsive, utility-first styling.
- **State Management:** React Query (`@tanstack/react-query`) for asynchronous data fetching and caching.
- **Icons & UI:** `lucide-react` for iconography and custom components.

### **Backend**
- **Framework:** FastAPI (Python) for high-performance, asynchronous REST APIs.
- **Server:** Uvicorn (ASGI) server.
- **Caching/State:** Redis (async client) for caching or rate-limiting.
- **AI/LLM:** OpenAI SDK & LangChain for orchestration.
- **Vector Database:** FAISS (Facebook AI Similarity Search) for fast, local vector storage.
- **File Processing:** `pypdf`/`PyPDF2` and `python-docx` for document parsing.

---

## 🧠 How the AI Works: Retrieval-Augmented Generation (RAG)

At its core, this application implements a complete **RAG pipeline** to allow users to "chat" with their documents without hallucination. Here is how the pipeline works step-by-step:

1. **Ingestion & Parsing (`upload` route):**
   - When a user uploads a PDF or DOCX file, the backend extracts the raw text.
   - The text is split into smaller, manageable "chunks" (usually around 500-1000 tokens) to ensure they fit into an LLM's context window.

2. **Vector Embeddings (`vector_service.py`):**
   - The chunks are passed to an embedding model (e.g., `text-embedding-ada-002` or `text-embedding-3-small` via OpenAI).
   - This converts the human-readable text into high-dimensional numerical vectors that represent the *semantic meaning* of the text.

3. **Vector Storage (`faiss_store.py`):**
   - These vectors are stored in a local **FAISS Vector Store**. FAISS is highly optimized for similarity search.

4. **Querying & Retrieval (`query` route / `rag_service.py`):**
   - When a user asks a question, the question itself is converted into an embedding.
   - The backend performs a mathematical **similarity search** (like cosine similarity) against the FAISS database to find the top `K` chunks of text most relevant to the question.
   
5. **Generation (LangChain & OpenAI):**
   - The retrieved chunks (context) are injected into a strict prompt alongside the user's original question.
   - The LLM reads the context and generates an accurate, grounded answer, completely eliminating hallucinations because it is constrained to the retrieved documents.

### Additional AI Features:
- **Audio Transcription (`whisper_service.py`):** Uses Whisper models to convert audio/video files into raw text, which can then be ingested into the RAG pipeline.
- **Summarization (`summarization_service.py`):** Uses LLMs to generate high-level summaries of large documents.

---

## 💼 What to Show to a Recruiter

When presenting this project to a recruiter or engineering manager, focus on the **complexity of the data pipeline** rather than just "calling an API." Here are your key talking points:

### 1. The Full RAG Pipeline
**What to say:** *"I built a custom RAG (Retrieval-Augmented Generation) architecture from scratch using LangChain and FAISS."*
**Why it matters:** It proves you understand how to solve the biggest problem with LLMs: hallucinations. Explain how you handled text chunking, embedding generation, and vector similarity search to ground the AI's answers in truth.

### 2. High-Performance Asynchronous Python
**What to say:** *"I chose FastAPI to handle heavy, I/O-bound AI tasks asynchronously."*
**Why it matters:** AI APIs take time to respond. By using FastAPI, `asyncio`, and Uvicorn, you ensured the server doesn't block other users while waiting for OpenAI to return an embedding or completion. 

### 3. Multimedia Processing
**What to say:** *"The app doesn't just handle text; it processes unstructured audio using Whisper."*
**Why it matters:** It shows you can handle multiple types of data ingestion. You built a system that can take a raw video file, transcribe it, chunk the transcript, embed it, and allow the user to immediately ask questions about the video.

### 4. Modern React Architecture
**What to say:** *"I managed complex asynchronous server state on the frontend using React Query."*
**Why it matters:** Handling loading states, errors, and caching for slow AI responses is difficult in React. React Query shows you know enterprise-standard ways to manage data fetching without relying on messy `useEffect` chains.

### 5. Local Vector Storage vs. Cloud
**What to say:** *"I implemented a local FAISS vector store to reduce latency and infrastructure costs."*
**Why it matters:** It demonstrates architectural decision-making. Instead of paying for a managed vector database like Pinecone right out of the gate, you built a self-contained, CPU-optimized vector store that is perfect for MVP scale.
