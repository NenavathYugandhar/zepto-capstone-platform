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

## Code Walkthrough: `ingest.py` (annotated)

```python
_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
# ^ Loads the embedding MODEL once, when this file is first imported.
#   Handing this to ChromaDB below means Chroma will automatically use
#   it to convert text into vectors — we never call the model directly.

_client = chromadb.PersistentClient(path=CHROMA_PATH)
# ^ PersistentClient means the vector data is SAVED TO DISK (in chroma_db/)
#   rather than living only in memory — it survives between runs, so you
#   don't have to re-embed the 8 documents every single time you start the app.


def get_collection():
    collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedding_fn,
        metadata={"hnsw:space": "cosine"},
        # ^ Tells Chroma's search index to rank results by COSINE similarity
        #   specifically (angle between vectors), matching the spec's
        #   requirement, rather than its other default distance metric.
    )
    if collection.count() == 0:
        # ^ .count() = how many chunks are already stored. On the very
        #   FIRST run, this is 0, so we ingest. On every run after that,
        #   the data's already there, so we skip re-ingesting.
        _ingest(collection)
    return collection


def _ingest(collection) -> None:
    doc_files = sorted(f for f in os.listdir(DOCS_DIR) if f.endswith(".txt"))
    # ^ sorted() ensures doc_01, doc_02, ... doc_08 always process in the
    #   same predictable order, regardless of how the OS lists files.
    documents, ids, metadatas = [], [], []

    for fname in doc_files:
        with open(os.path.join(DOCS_DIR, fname), encoding="utf-8") as f:
            text = f.read().strip()
        doc_id = os.path.splitext(fname)[0]
        # ^ os.path.splitext("doc_01.txt") -> ("doc_01", ".txt"); [0] keeps
        #   just "doc_01" — this becomes the chunk's ID used later in
        #   the API response's "sources" field.
        documents.append(text)
        ids.append(doc_id)
        metadatas.append({"source": fname})

    collection.add(documents=documents, ids=ids, metadatas=metadatas)
    # ^ ONE call embeds all 8 documents AND stores them — Chroma handles
    #   calling the embedding model internally because we gave it
    #   `embedding_function` when the collection was created above.
```

## Code Walkthrough: `graph.py` (annotated)

```python
class GraphState(TypedDict):
    query: str
    intent: str
    retrieved_chunks: list[dict]
    answer: str
    sources: list[str]
    confidence: float
# ^ TypedDict describes the SHAPE of data that flows through the graph —
#   every node receives a GraphState and returns an updated GraphState.
#   This is just documentation/type-checking, not enforced at runtime,
#   but it's what the spec's "TypedDict state" requirement refers to.


def classify_intent(state: GraphState) -> GraphState:
    query_lower = state["query"].lower()

    if _mock_mode():
        intent = (
            "policy_question"
            if any(keyword in query_lower for keyword in POLICY_KEYWORDS)
            # ^ any(...) returns True if AT LEAST ONE keyword ("delivery",
            #   "return", etc.) appears anywhere in the lowercased query.
            else "general_question"
        )
    else:
        from llm import llm_classify_intent
        # ^ Imported HERE, inside the else branch, not at the top of the
        #   file — so mock mode never even tries to load the LLM-related
        #   code, keeping mock mode fully independent of any API key.
        intent = llm_classify_intent(state["query"])

    return {**state, "intent": intent}
    # ^ {**state, "intent": intent} means: "copy everything from the old
    #   state, then overwrite just the 'intent' field" — this is how you
    #   update one field of a dict without mutating the original in place.


def _route_on_intent(state: GraphState) -> str:
    return state["intent"]
    # ^ This function's ONLY job is to tell the graph which node to go to
    #   next, based on the intent classify_intent just set. Returns
    #   exactly "policy_question" or "general_question" — which must
    #   match the keys in the routing dict passed to add_conditional_edges.


def retrieve_and_answer(state: GraphState) -> GraphState:
    collection = get_collection()
    results = collection.query(query_texts=[state["query"]], n_results=3)
    # ^ This ALWAYS runs, regardless of MOCK_LLM — embeds the query and
    #   finds the top-3 closest chunks. No LLM or API key involved here at all.
    ids = results["ids"][0]
    docs = results["documents"][0]
    # ^ Chroma's .query() supports searching MULTIPLE queries at once, so
    #   results are nested one level: results["ids"] is a LIST OF LISTS
    #   (one inner list per query). We only sent 1 query, so [0] gets its results.

    if _mock_mode():
        top_chunk_snippet = retrieved_chunks[0]["text"][:200]
        # ^ [:200] takes just the first 200 characters — a short preview,
        #   not the whole document, per the spec's canned-template format.
        answer = f"Based on the retrieved context: {top_chunk_snippet}"
        confidence = 1.0
        # ^ Fixed 1.0 because there's no real "confidence" concept in
        #   mock mode — it's not a model's output, just a template.
    else:
        from llm import llm_answer_with_context
        context = "\n\n".join(chunk["text"] for chunk in retrieved_chunks)
        answer = llm_answer_with_context(state["query"], context)
        confidence = 0.85

    return {**state, "retrieved_chunks": retrieved_chunks, "answer": answer,
            "sources": ids, "confidence": confidence}


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_and_answer", retrieve_and_answer)
    graph.add_node("direct_answer", direct_answer)

    graph.set_entry_point("classify_intent")
    # ^ Every request starts here, no matter what.

    graph.add_conditional_edges(
        "classify_intent",
        _route_on_intent,
        {"policy_question": "retrieve_and_answer", "general_question": "direct_answer"},
        # ^ This dict maps _route_on_intent's return value to the next
        #   node name. Return "policy_question" -> go to retrieve_and_answer.
        #   Return "general_question" -> go to direct_answer.
    )
    graph.add_edge("retrieve_and_answer", END)
    graph.add_edge("direct_answer", END)
    # ^ Both branches lead straight to END — this graph has no loops,
    #   just one decision point and two possible one-step paths.

    return graph.compile()
    # ^ .compile() turns the node/edge definitions into a runnable object
    #   with an .invoke(state) method — this is what main.py calls.
```

## Code Walkthrough: `main.py` (annotated)

```python
app = FastAPI(title="Zepto Support Assistant")
_graph = build_graph()
# ^ The graph is built ONCE, when the server starts — not rebuilt on
#   every single request, which would be wasteful.


@app.post("/ask", response_model=AskResponse)
# ^ @app.post(...) registers this function to handle POST requests to /ask.
#   response_model=AskResponse tells FastAPI to validate whatever this
#   function returns against the AskResponse schema BEFORE sending it
#   back — if something doesn't match (wrong type, missing field), FastAPI
#   raises an error instead of silently sending bad data to the caller.
def ask_endpoint(request: AskRequest) -> AskResponse:
    # ^ `request: AskRequest` — FastAPI automatically reads the incoming
    #   JSON body, validates it matches AskRequest's shape ({"query": str}),
    #   and hands it to us as a real Python object, not a raw dict.
    result = _graph.invoke({
        "query": request.query,
        "intent": "", "retrieved_chunks": [], "answer": "", "sources": [], "confidence": 0.0,
    })
    # ^ .invoke() runs the ENTIRE graph — classify_intent, then whichever
    #   branch it routes to — and returns the FINAL state after both
    #   nodes (or just one) have run.
    return AskResponse(
        answer=result["answer"], sources=result["sources"], confidence=result["confidence"],
    )
    # ^ Pulls just the 3 relevant fields out of the graph's final state
    #   and wraps them in the AskResponse schema.
```
