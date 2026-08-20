from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(
        self,
        search_client: SearchClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.search_client = search_client or SearchClient()
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""
        docs = self.search_client.search(
            query=state.request.query,
            max_results=state.request.max_sources,
        )
        state.sources = docs

        raw_notes = "\n\n".join(
            [
                f"[{i+1}] {d.title}\nURL: {d.url or 'N/A'}\nExcerpt: {d.snippet}"
                for i, d in enumerate(docs)
            ]
        )

        try:
            system_prompt = (
                "You are an expert researcher. Extract key factual claims, findings, and technical "
                "details from the sources. Group findings logically and cite sources with [1], [2]."
            )
            user_prompt = f"Query: {state.request.query}\n\nRetrieved Sources:\n{raw_notes}"
            res = self.llm_client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
            state.research_notes = res.content
        except Exception:
            state.research_notes = f"Research findings based on {len(docs)} sources:\n\n{raw_notes}"

        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=state.research_notes,
                metadata={"num_sources": len(docs)},
            )
        )
        state.add_trace_event("researcher.done", {"num_sources": len(docs)})
        return state
