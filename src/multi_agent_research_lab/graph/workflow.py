from typing import Any

from langgraph.graph import END, START, StateGraph

from multi_agent_research_lab.agents import (
    AnalystAgent,
    CriticAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.state import ResearchState


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Orchestrates handoffs between supervisor, researcher, analyst, and writer.
    """

    def __init__(
        self,
        supervisor: BaseAgent | None = None,
        researcher: BaseAgent | None = None,
        analyst: BaseAgent | None = None,
        writer: BaseAgent | None = None,
        critic: BaseAgent | None = None,
    ) -> None:
        self.supervisor = supervisor or SupervisorAgent()
        self.researcher = researcher or ResearcherAgent()
        self.analyst = analyst or AnalystAgent()
        self.writer = writer or WriterAgent()
        self.critic = critic or CriticAgent()

    def _route_condition(self, state: ResearchState) -> str:
        """Select next node based on the latest route recorded in state."""
        if not state.route_history:
            return "done"
        last_route = state.route_history[-1]
        if last_route in ("researcher", "analyst", "writer"):
            return last_route
        return "done"

    def build(self) -> Any:
        """Create a LangGraph graph with nodes, conditional edges, and stop condition."""
        builder = StateGraph(ResearchState)

        # Register nodes
        builder.add_node("supervisor", self.supervisor.run)
        builder.add_node("researcher", self.researcher.run)
        builder.add_node("analyst", self.analyst.run)
        builder.add_node("writer", self.writer.run)

        # Entry edge
        builder.add_edge(START, "supervisor")

        # Conditional edges from supervisor
        builder.add_conditional_edges(
            "supervisor",
            self._route_condition,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": END,
            },
        )

        # Loop back from worker nodes to supervisor
        builder.add_edge("researcher", "supervisor")
        builder.add_edge("analyst", "supervisor")
        builder.add_edge("writer", "supervisor")

        return builder.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final ResearchState."""
        graph = self.build()
        raw_output = graph.invoke(state)
        if isinstance(raw_output, ResearchState):
            return raw_output
        return ResearchState.model_validate(raw_output)

