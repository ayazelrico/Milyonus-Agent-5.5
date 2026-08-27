---
name: rag-retrieval
description: Build a Retrieval-Augmented Generation system (chunk, embed, search)
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - rag
    - embeddings
    - vector
    - llm
    - retrieval
    category: ai
    requires_toolsets: []
    provenance: official
---

# RAG (Retrieval-Augmented Generation)
Goal: inject relevant source text into the LLM's context when generating —
reduces hallucination, supplies fresh/private knowledge.
## Pipeline
1. **Load & chunk:** split documents into ~300–800 token chunks with 10–20% overlap. Preserve semantic boundaries (paragraph/heading).
2. **Embed:** turn each chunk into a vector with an embedding model (e.g. OpenAI `text-embedding-3-small`, local `bge`/`e5`).
3. **Store:** write vectors to a vector store (sqlite-vec, FAISS, pgvector, Qdrant). Keep metadata (source, title) alongside.
4. **Retrieve:** embed the query -> find the nearest k chunks (cosine). Typical k=4–8.
5. **Rerank (optional):** rerank the top-k with a cross-encoder.
6. **Generate:** pass the retrieved chunks to the prompt **as sources**; instruct the model to "answer only from the given context, else say you don't know".
## Quality tips
- **Chunk size** is the most critical knob: too large -> noise, too small -> broken context.
- **Hybrid search:** combine vector + keyword (BM25); good for exact terms.
- **Cite sources:** state which chunk an answer came from (trust + auditability).
- **Evaluate:** measure "retrieval hit rate" and "answer correctness" over a QA set.
- In Milyonus the embedding layer is optional (`sqlite-vec`); it is also used for dedup / negative-memory similarity.
