from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.max_iterations = self.settings.max_iterations

    def decide_next_route(self, state: ResearchState) -> str:
        """Inspect state and determine the next agent route.

        Routing policy:
        1. Guard: Stop if reached max_iterations or errors encountered.
        2. Guard: Stop if final_answer is already populated.
        3. Missing sources -> 'researcher'
        4. Has sources, missing analysis_notes -> 'analyst'
        5. Has analysis_notes, missing final_answer -> 'writer'
        6. Otherwise -> 'done'
        """
        if state.iteration >= self.max_iterations:
            return "done"

        if state.errors:
            return "done"

        if state.final_answer and state.final_answer.strip():
            return "done"

        if not state.sources:
            return "researcher"

        if not state.analysis_notes or not state.analysis_notes.strip():
            return "analyst"

        if not state.final_answer or not state.final_answer.strip():
            return "writer"

        return "done"

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route and record trace event."""
        next_route = self.decide_next_route(state)
        state.record_route(next_route)
        state.add_trace_event(
            "supervisor.routed",
            {"route": next_route, "iteration": state.iteration},
        )
        return state
