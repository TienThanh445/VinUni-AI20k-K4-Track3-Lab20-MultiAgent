from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes` with comparative analysis and evidence evaluation."""
        if not state.sources and not state.research_notes:
            state.errors.append("Analyst: No sources or research notes available for analysis.")
            return state

        system_prompt = (
            "You are an expert technical analyst. Your task is to critically analyze research:\n"
            "1. Extract core claims, mechanisms, and architectures.\n"
            "2. Compare viewpoints, trade-offs (e.g. latency vs accuracy, cost vs quality).\n"
            "3. Assess source reliability and flag weak assumptions.\n"
            "4. Provide structured analytical notes for the writer, citing sources as [1], [2]."
        )
        user_prompt = (
            f"Research Query: {state.request.query}\n"
            f"Target Audience: {state.request.audience}\n\n"
            f"Research Notes & Sources:\n{state.research_notes or 'No research notes available.'}"
        )

        try:
            res = self.llm_client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            state.analysis_notes = res.content
            tokens_meta = {"input_tokens": res.input_tokens, "output_tokens": res.output_tokens}
        except Exception as exc:
            state.analysis_notes = (
                f"Comparative Analysis for '{state.request.query}':\n"
                f"- Synthesis of {len(state.sources)} source(s).\n"
                f"- Notes: {state.research_notes[:300] if state.research_notes else 'N/A'}"
            )
            tokens_meta = {"error": str(exc)}

        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=state.analysis_notes,
                metadata=tokens_meta,
            )
        )
        state.add_trace_event("analyst.done", {"notes_length": len(state.analysis_notes)})
        return state
