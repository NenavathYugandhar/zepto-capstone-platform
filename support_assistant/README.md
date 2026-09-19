# Support Assistant

A small GenAI service answering questions grounded in Zepto's own policy documents, using a
LangGraph-orchestrated flow, ChromaDB retrieval, and a FastAPI wrapper. All LLM calls are
gated behind `MOCK_LLM` — left at its default, the entire service runs deterministically with
no API key, no signup, and no network call to any LLM provider.

## Setup

```
pip install -r requirements.txt
```

## Run

```
python main.py
```

This starts the API on `http://localhost:7860`. The first request that needs retrieval will
lazily download the `all-MiniLM-L6-v2` model and build the ChromaDB collection from `docs/`
(cached afterward) — this requires network access to Hugging Face **once**; it is not needed
for `docker build` itself, only the first real request.

> **A note on this repository's own development environment:** this project was built and
> committed from a corporate network that blocks `huggingface.co` at the proxy level (the
> same restriction documented in the author's earlier `RAG App` project). Because of that,
> the code below could not be executed end-to-end in that environment to *capture* real
> request/response transcripts for this README — the two example calls below are the exact
> commands to run; **run them yourself once installed on an unrestricted network and record
> the real JSON output here before submitting**, since the assignment requires actual captured
> output, not illustrative output.

### Example calls (run these and paste the real output here)

```bash
curl -X POST http://localhost:7860/ask -H "Content-Type: application/json" \
     -d '{"query": "What is your delivery fee?"}'
# Expected: intent=policy_question -> retrieve_and_answer.
# Mock-mode answer will look like:
# {"answer": "Based on the retrieved context: Zepto delivers grocery and household
#  essentials to serviceable pin codes within 10 to 30 minutes...", "sources": ["doc_01"],
#  "confidence": 1.0}

curl -X POST http://localhost:7860/ask -H "Content-Type: application/json" \
     -d '{"query": "What is the capital of France?"}'
# Expected: intent=general_question -> direct_answer.
# Mock-mode answer:
# {"answer": "I can only answer questions about Zepto policies right now.",
#  "sources": [], "confidence": 1.0}
```

## Run with Docker

```
docker build -t zepto-support-assistant .
docker run -p 7860:7860 zepto-support-assistant
```

## Optional extension: real LLM (MOCK_LLM=0)

Requires a free Groq API key (console.groq.com) exported as `GROQ_API_KEY`:

```
export MOCK_LLM=0
export GROQ_API_KEY=your_key_here
python main.py
```

## Architecture

```
Query
  |
  v
[classify_intent]  <- keyword heuristic (mock) or LLM call (MOCK_LLM=0), in graph.py
  |
  |-- policy_question --> [retrieve_and_answer] --> END
  |                          - embeds query (all-MiniLM-L6-v2, ingest.py)
  |                          - queries ChromaDB collection "zepto_policies" (cosine similarity,
  |                            top-3 chunks) -- runs for real in BOTH modes
  |                          - mock: canned "Based on the retrieved context: ..." template
  |                          - MOCK_LLM=0: prompts the LLM (prompts.py) grounded in the chunks
  |
  |-- general_question --> [direct_answer] --> END
                             - mock: fixed canned string, no LLM call
                             - MOCK_LLM=0: prompts the LLM directly, no retrieval
```

**Ingestion & embedding** (`ingest.py`): the 8 policy `.txt` files under `docs/` are each
treated as one chunk (given their short length), embedded with `sentence-transformers`'
`all-MiniLM-L6-v2`, and stored in a persistent ChromaDB collection (`zepto_policies`,
configured for cosine similarity via `hnsw:space: cosine`). Ingestion runs once, lazily, the
first time the collection is empty.

**Retrieval** (`graph.py`'s `retrieve_and_answer` node): embeds the incoming query with the
same model and calls `collection.query(..., n_results=3)` to get the top-3 most similar
chunks. This step is identical in both `MOCK_LLM` states — it needs no API key and makes no
network call to any LLM provider.

**Generation** (`retrieve_and_answer` and `direct_answer`): this is the **only** part gated by
`MOCK_LLM`. In the default/mock state, generation is fully deterministic Python string
templating — no LLM is called anywhere in the service. When `MOCK_LLM=0`, generation instead
calls a real LLM (Groq, via `llm.py`) using the structured prompt template in `prompts.py`.

**Structured output**: `schemas.py` defines the `AskResponse` Pydantic model
(`answer`, `sources`, `confidence`). In mock mode this is populated deterministically by the
graph nodes themselves. In the optional real-LLM path, `llm.py`'s `validate_with_retry`
validates the LLM's raw JSON output against this schema and retries up to 2 additional times
with a corrective prompt before returning a clearly marked error response.

**API** (`main.py`): a single `POST /ask` FastAPI endpoint takes `{"query": str}`, invokes the
compiled LangGraph app, and returns the validated `AskResponse`.
