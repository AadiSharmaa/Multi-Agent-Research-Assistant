"""
FastAPI server that exposes the LangGraph research pipeline over SSE.

Single endpoint:
    POST /api/research  { "query": "..." }
    → Server-Sent Events stream with per-node progress + final report
"""

import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from graph import app as research_app


# ── FastAPI setup ────────────────────────────────────────────────────────────

app = FastAPI(
    title="Multi-Agent Research Assistant",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request schema ───────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str


# ── SSE helpers ──────────────────────────────────────────────────────────────

def _sse_event(payload: dict) -> str:
    """Format a dict as an SSE `data:` line."""
    return f"data: {json.dumps(payload)}\n\n"


# ── Endpoint ─────────────────────────────────────────────────────────────────

@app.post("/api/research")
async def research(request: ResearchRequest):
    """Stream research progress via Server-Sent Events.

    Each SSE payload contains:
        • node   – name of the node that just executed
        • data   – the state delta returned by that node

    The final event has node="complete" and carries the finished
    draft_summary so the client can render the report immediately.
    """

    async def event_stream():
        initial_state = {
            "query": request.query,
            "search_queries": [],
            "raw_context": [],
            "draft_summary": "",
            "revision_notes": "",
            "iteration_count": 0,
        }

        final_summary = ""

        # stream_mode="updates" yields {node_name: state_delta} per step
        async for event in research_app.astream(
            initial_state,
            stream_mode="updates",
        ):
            for node_name, node_output in event.items():
                # Track the latest draft so we can emit it at the end
                if "draft_summary" in node_output:
                    final_summary = node_output["draft_summary"]

                # Build a slim payload (skip raw_context to keep events small)
                payload = {
                    "node": node_name,
                    "data": {
                        k: v
                        for k, v in node_output.items()
                        if k != "raw_context"
                    },
                }

                # Include a context_count so the UI can show progress
                if "raw_context" in node_output:
                    payload["data"]["context_pages_added"] = len(
                        node_output["raw_context"]
                    )

                yield _sse_event(payload)

        # Final event with the completed report
        yield _sse_event({
            "node": "complete",
            "data": {"draft_summary": final_summary},
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",       # disable nginx buffering if proxied
        },
    )


# ── Dev entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
