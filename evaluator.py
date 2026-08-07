"""
Trajectory Evaluator – LLM-as-a-Judge for multi-agent execution auditing.

Passes the full execution trajectory (step-by-step inputs, outputs, and
iteration metadata) to a structured LLM judge that scores tool correctness,
synthesis faithfulness, step efficiency, and identifies root-cause failures.
"""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Structured output schemas ────────────────────────────────────────────────

class StepScore(BaseModel):
    """Evaluation score for an individual agent step."""

    step_name: str = Field(description="Name of the agent step being evaluated")
    score: float = Field(description="Score between 0.0 and 1.0")
    feedback: str = Field(description="Critique of this specific step")


class TrajectoryEvaluation(BaseModel):
    """Full trajectory audit result returned by the LLM judge."""

    tool_correctness_score: float = Field(
        description="0.0 - 1.0 rating search query selection and scraping quality"
    )
    synthesis_faithfulness_score: float = Field(
        description=(
            "0.0 - 1.0 rating how accurately raw context was summarized "
            "without hallucination"
        )
    )
    step_efficiency_score: float = Field(
        description=(
            "0.0 - 1.0 rating on loop efficiency and absence of "
            "repetitive actions"
        )
    )
    overall_trajectory_score: float = Field(
        description="0.0 - 1.0 overall execution quality"
    )
    primary_failure_point: str = Field(
        description=(
            "Name of the node where the primary failure occurred, "
            "or 'None' if successful"
        )
    )
    root_cause_analysis: str = Field(
        description=(
            "Detailed diagnostic explaining why the trajectory succeeded "
            "or where and why it broke down"
        )
    )
    step_scores: list[StepScore] = Field(
        description="Detailed breakdown per agent step"
    )


# ── Evaluator function ───────────────────────────────────────────────────────

def evaluate_trajectory(
    trajectory: list[dict],
    final_report: str,
    original_query: str,
) -> TrajectoryEvaluation:
    """Evaluate the full execution trajectory using LLM-as-a-Judge.

    Args:
        trajectory: List of trajectory event dicts logged by each agent node.
        final_report: The final draft_summary produced by the pipeline.
        original_query: The user's original research question.

    Returns:
        A TrajectoryEvaluation with scores, failure attribution, and
        per-step feedback.
    """
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    structured_llm = llm.with_structured_output(TrajectoryEvaluation)

    with open("eval_prompt.txt", "r") as f:
        system_prompt = f.read()

    user_prompt = (
        "## User Original Query\n"
        f"{original_query}\n\n"
        "## Final Generated Report\n"
        f"{final_report}\n\n"
        "## Full Execution Trajectory Log\n"
        f"{json.dumps(trajectory, indent=2)}"
    )

    logger.info("Running trajectory evaluation for query: %s", original_query)

    result = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    logger.info(
        "Trajectory evaluation complete – overall score: %.2f",
        result.overall_trajectory_score,
    )

    return result
