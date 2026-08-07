"""
Agent nodes for the multi-agent research graph.

Three distinct LLM-powered nodes:
  1. Researcher  – generates search queries, scrapes via Jina Reader
  2. Synthesizer – distils raw context into a structured report
  3. Validator   – checks the draft against the original query
"""

import json
import operator

import httpx
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from state import ResearchState

load_dotenv()




# ── Pydantic schema for structured validator output ──────────────────────────

class ValidationResult(BaseModel):
    """Structured output returned by the validation agent."""

    is_valid: bool = Field(
        description="True if the draft comprehensively answers the query."
    )
    revision_notes: str = Field(
        default="",
        description="Specific feedback on what is missing or needs improvement.",
    )


# ── Helper: DuckDuckGo search → Jina Reader markdown ────────────────────────

def search_and_scrape(query: str) -> list[str]:
    """Return clean markdown for the top-3 DuckDuckGo results.

    Each result URL is routed through https://r.jina.ai/ which returns
    a reader-friendly markdown version of the page.
    """
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=3))

    markdown_pages: list[str] = []
    for result in results:
        url = result["href"]
        jina_url = f"https://r.jina.ai/{url}"
        try:
            resp = httpx.get(jina_url, timeout=30, follow_redirects=True)
            if resp.status_code == 200:
                markdown_pages.append(
                    f"<!-- source: {url} -->\n{resp.text}"
                )
        except httpx.RequestError:
            # Skip unreachable pages; remaining sources are still useful
            continue

    return markdown_pages


# ── Node 1 – Researcher ─────────────────────────────────────────────────────

def researcher_node(state: ResearchState) -> dict:
    """Generate 2 optimised search terms, scrape results, append to context.

    Uses ChatGroq (Llama-3.1-8b) for fast query generation, then delegates
    to *search_and_scrape* for retrieval.  Increments iteration_count by 1.
    """
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

    system_prompt = (
        "You are a research query optimiser. "
        "Given a user's research question and optional revision notes, "
        "generate exactly 2 targeted search terms that will surface "
        "comprehensive, high-quality information.\n"
        "Respond with ONLY a JSON array of 2 strings – no explanation."
    )

    user_prompt = f"Research question: {state['query']}"
    if state.get("revision_notes"):
        user_prompt += f"\n\nRevision feedback to address:\n{state['revision_notes']}"

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    search_terms: list[str] = json.loads(response.content)

    # Scrape results for every generated search term
    all_markdown: list[str] = []
    for term in search_terms:
        all_markdown.extend(search_and_scrape(term))

    iteration = state.get("iteration_count", 0) + 1

    # Log the trajectory event for the Researcher
    trajectory_event = {
        "step": "researcher",
        "iteration": iteration,
        "inputs": {
            "query": state["query"],
            "revision_notes": state.get("revision_notes", ""),
        },
        "outputs": {
            "search_queries": search_terms,
            "docs_retrieved_count": len(all_markdown),
            "doc_snippets": [doc[:150] + "..." for doc in all_markdown],
        },
    }

    return {
        "search_queries": search_terms,
        "raw_context": all_markdown,                       # appended via operator.add
        "iteration_count": iteration,
        "trajectory": [trajectory_event],
    }


# ── Node 2 – Synthesizer ────────────────────────────────────────────────────

def synthesizer_node(state: ResearchState) -> dict:
    """Ingest all accumulated raw_context and produce a markdown report.

    Uses ChatGroq (Llama-3.3-70b) which handles the
    large context window needed for the concatenated source material.
    """
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)

    combined_context = "\n\n---\n\n".join(state["raw_context"])

    system_prompt = (
        "You are an expert research synthesiser. "
        "Given a research query and a large collection of scraped source material, "
        "produce a comprehensive, well-structured **markdown** report.\n\n"
        "Requirements:\n"
        "- Use clear section headings (##, ###)\n"
        "- Include bullet points for key findings\n"
        "- Cite or reference source URLs where available\n"
        "- Highlight areas of consensus and disagreement among sources\n"
        "- End with a concise conclusion"
    )

    user_prompt = (
        f"## Research Query\n{state['query']}\n\n"
        f"## Source Material\n{combined_context}"
    )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    # Log the trajectory event for the Synthesizer
    trajectory_event = {
        "step": "synthesizer",
        "iteration": state.get("iteration_count", 0),
        "inputs": {
            "query": state["query"],
            "context_docs_count": len(state["raw_context"]),
        },
        "outputs": {
            "draft_summary_length": len(response.content),
            "draft_summary_preview": response.content[:300] + "...",
        },
    }

    return {
        "draft_summary": response.content,
        "trajectory": [trajectory_event],
    }


# ── Node 3 – Validator ──────────────────────────────────────────────────────

def validator_node(state: ResearchState) -> dict:
    """Compare draft_summary against the original query for completeness.

    Uses ChatGroq with structured output (Pydantic) to return a
    ValidationResult with *is_valid* and *revision_notes*.
    An empty revision_notes string signals approval to the router.
    """
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    structured_llm = llm.with_structured_output(ValidationResult)

    system_prompt = (
        "You are a rigorous research-quality validator. "
        "Evaluate whether the draft report fully and accurately answers "
        "the original research query.\n\n"
        "If the report is satisfactory, set is_valid = true and leave "
        "revision_notes empty.\n"
        "If not, set is_valid = false and provide specific, actionable "
        "revision notes describing what is missing or inaccurate."
    )

    user_prompt = (
        f"## Original Query\n{state['query']}\n\n"
        f"## Draft Report\n{state['draft_summary']}"
    )

    result: ValidationResult = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    revision = result.revision_notes if not result.is_valid else ""

    # Log the trajectory event for the Validator
    trajectory_event = {
        "step": "validator",
        "iteration": state.get("iteration_count", 0),
        "inputs": {
            "query": state["query"],
            "draft_summary_length": len(state.get("draft_summary", "")),
        },
        "outputs": {
            "is_valid": result.is_valid,
            "revision_notes": revision,
        },
    }

    return {
        "revision_notes": revision,
        "trajectory": [trajectory_event],
    }
