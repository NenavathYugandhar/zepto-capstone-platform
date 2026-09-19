"""FastAPI wrapper exposing the LangGraph-orchestrated support assistant."""
from fastapi import FastAPI

from graph import build_graph
from schemas import AskRequest, AskResponse

app = FastAPI(title="Zepto Support Assistant")
_graph = build_graph()


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest) -> AskResponse:
    result = _graph.invoke(
        {
            "query": request.query,
            "intent": "",
            "retrieved_chunks": [],
            "answer": "",
            "sources": [],
            "confidence": 0.0,
        }
    )
    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
