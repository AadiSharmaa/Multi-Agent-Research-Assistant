"""
LangGraph state machine wiring the research assistant pipeline.

Graph flow:
    researcher → synthesizer → validator → (conditional)
                                             ├─ valid          → END
                                             ├─ invalid, < 3   → researcher
                                             └─ invalid, >= 3  → END (failsafe)
"""

from langgraph.graph import END, StateGraph

from agents import researcher_node, synthesizer_node, validator_node
from state import ResearchState


# ── Conditional router ───────────────────────────────────────────────────────

def route_after_validation(state: ResearchState) -> str:
    """Decide the next node after the validator runs.

    • No revision notes → report accepted → END
    • Revision notes present, but under the loop cap → retry research
    • Revision notes present, at or past the cap → force finish (failsafe)
    """
    is_valid = state.get("revision_notes", "") == ""

    if is_valid:
        return END

    if state.get("iteration_count", 0) < 3:
        return "researcher"

    # Failsafe: too many iterations, ship what we have
    return END


# ── Build the graph ──────────────────────────────────────────────────────────

workflow = StateGraph(ResearchState)

# Register nodes
workflow.add_node("researcher", researcher_node)
workflow.add_node("synthesizer", synthesizer_node)
workflow.add_node("validator", validator_node)

# Entry point
workflow.set_entry_point("researcher")

# Linear edges
workflow.add_edge("researcher", "synthesizer")
workflow.add_edge("synthesizer", "validator")

# Conditional edge from the validator
workflow.add_conditional_edges(
    source="validator",
    path=route_after_validation,
    path_map={
        END: END,
        "researcher": "researcher",
    },
)

# Compile and export
app = workflow.compile()
