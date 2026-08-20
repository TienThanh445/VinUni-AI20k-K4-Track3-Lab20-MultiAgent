from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes with proper citations."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer` with synthesized report and citations."""
        if not state.analysis_notes and not state.research_notes:
            state.errors.append("Writer: No analysis or research notes available to synthesize.")
            return state

        sources_list = "\n".join(
            [
                f"[{i+1}] {d.title} ({d.url or 'internal corpus'})"
                for i, d in enumerate(state.sources)
            ]
        )

        system_prompt = (
            "You are an expert research technical writer. Your task is to produce a rigorous, "
            f"clear, and structured final report for: {state.request.audience}.\n\n"
            "Requirements:\n"
            "1. Organize into logical sections (e.g. Executive Summary, Technical Analysis, "
            "Trade-offs & Practical Recommendations).\n"
            "2. Ground key facts and arguments with bracketed numeric citations (e.g. [1], [2]) "
            "strictly corresponding to the provided sources list.\n"
            "3. Conclude with a 'References' section explicitly mapping [1], [2] to sources."
        )
        user_prompt = (
            f"Research Question: {state.request.query}\n\n"
            f"Analysis Notes & Insights:\n{state.analysis_notes or state.research_notes}\n\n"
            f"Available Sources for Citation:\n{sources_list or 'No explicit sources available.'}"
        )

        try:
            res = self.llm_client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            state.final_answer = res.content
            tokens_meta = {"input_tokens": res.input_tokens, "output_tokens": res.output_tokens}
        except Exception as exc:
            state.final_answer = (
                f"## Final Report: {state.request.query}\n\n"
                f"### Analysis Synthesis\n{state.analysis_notes or state.research_notes}\n\n"
                f"### References\n{sources_list}"
            )
            tokens_meta = {"error": str(exc)}

        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=state.final_answer,
                metadata=tokens_meta,
            )
        )
        state.add_trace_event("writer.done", {"final_answer_length": len(state.final_answer)})
        return state
