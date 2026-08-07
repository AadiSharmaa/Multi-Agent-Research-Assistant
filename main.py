"""
FastAPI server that exposes the LangGraph research pipeline over SSE.

Endpoints:
    POST /api/research   { "query": "..." }  → SSE stream with progress + report
    GET  /api/evaluate                        → trajectory evaluation of last run
"""

import json
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# --- Rate-limiting (Denial-of-Wallet protection) ---
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from graph import app as research_app
from export_service import export_to_docs
from evaluator import evaluate_trajectory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── FastAPI & Limiter setup ──────────────────────────────────────────────────

# Initialize the rate limiter based on the user's IP address
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Multi-Agent Research Assistant",
    version="0.1.0",
)

# Attach the limiter to the FastAPI app instance
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory store for the last completed research session
_last_session: dict = {}


# ── Request schema ───────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str


class ExportRequest(BaseModel):
    summary: str
    title: str


# ── SSE helpers ──────────────────────────────────────────────────────────────

def _sse_event(payload: dict) -> str:
    """Format a dict as an SSE `data:` line."""
    return f"data: {json.dumps(payload)}\n\n"


# ── Endpoint ─────────────────────────────────────────────────────────────────

@app.post("/api/research")
@limiter.limit("5/minute")  # Max 5 requests per minute per IP
async def research(request: Request, body: ResearchRequest):
    """Stream research progress via Server-Sent Events.

    Each SSE payload contains:
        • node   – name of the node that just executed
        • data   – the state delta returned by that node

    The final event has node="complete" and carries the finished
    draft_summary so the client can render the report immediately.
    """

    async def event_stream():
        initial_state = {
            "query": body.query,
            "search_queries": [],
            "raw_context": [],
            "draft_summary": "",
            "revision_notes": "",
            "iteration_count": 0,
            "trajectory": [],
        }

        final_summary = ""
        accumulated_trajectory: list[dict] = []

        # stream_mode="updates" yields {node_name: state_delta} per step
        async for event in research_app.astream(
            initial_state,
            stream_mode="updates",
        ):
            for node_name, node_output in event.items():
                # Track the latest draft so we can emit it at the end
                if "draft_summary" in node_output:
                    final_summary = node_output["draft_summary"]

                # Accumulate trajectory events for post-run evaluation
                if "trajectory" in node_output:
                    accumulated_trajectory.extend(node_output["trajectory"])

                # Build a slim payload (skip raw_context & trajectory to keep events small)
                payload = {
                    "node": node_name,
                    "data": {
                        k: v
                        for k, v in node_output.items()
                        if k not in ("raw_context", "trajectory")
                    },
                }

                # Include a context_count so the UI can show progress
                if "raw_context" in node_output:
                    payload["data"]["context_pages_added"] = len(
                        node_output["raw_context"]
                    )

                yield _sse_event(payload)

        # Store the completed session for trajectory evaluation
        _last_session.update({
            "query": body.query,
            "final_summary": final_summary,
            "trajectory": accumulated_trajectory,
        })

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


# ── Evaluate endpoint ────────────────────────────────────────────────────────

@app.get("/api/evaluate")
async def evaluate_last_run():
    """Run the trajectory evaluator on the last completed research session.

    Returns a structured JSON report with scores for tool correctness,
    synthesis faithfulness, step efficiency, and root-cause failure analysis.
    """
    if not _last_session:
        return JSONResponse(
            status_code=404,
            content={"detail": "No completed research session to evaluate. Run /api/research first."},
        )

    try:
        result = evaluate_trajectory(
            trajectory=_last_session["trajectory"],
            final_report=_last_session["final_summary"],
            original_query=_last_session["query"],
        )
        return result.model_dump()
    except Exception as e:
        logger.error("Trajectory evaluation failed:\n%s", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
        )


# ── Export endpoint ───────────────────────────────────────────────────────────

@app.post("/api/export/docs")
async def export_docs(request: ExportRequest):
    """Create a Google Doc from the research summary and return its URL."""
    try:
        url = export_to_docs(request.summary, request.title)
        return {"url": url}
    except Exception as e:
        logger.error("Google Docs export failed:\n%s", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)},
        )


# ── Dev entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
