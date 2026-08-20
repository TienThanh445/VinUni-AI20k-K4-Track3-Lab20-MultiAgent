"""Command-line entrypoint for the lab starter."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import LabError, StudentTodoError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_comparative_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import setup_tracing
from multi_agent_research_lab.services.llm_client import LLMClient

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    setup_tracing(settings)


def _parse_query(query: str) -> ResearchQuery:
    try:
        return ResearchQuery(query=query)
    except ValidationError as exc:
        console.print(
            Panel.fit(
                f"Invalid query: {exc.errors()[0]['msg']}",
                title="Input Error",
                style="red",
            )
        )
        raise typer.Exit(code=1) from exc


def _run_baseline(query_str: str) -> ResearchState:
    req = _parse_query(query_str)
    state = ResearchState(request=req)
    llm_client = LLMClient()
    response = llm_client.complete(
        system_prompt=(
            "You are an expert research assistant. Provide a structured, "
            "insightful, and comprehensive answer to the user's research query."
        ),
        user_prompt=req.query,
    )
    state.final_answer = response.content
    state.agent_results.append(
        AgentResult(
            agent=AgentName.WRITER,
            content=response.content,
            metadata={
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
    )
    return state


def _run_multi_agent(query_str: str) -> ResearchState:
    state = ResearchState(request=_parse_query(query_str))
    workflow = MultiAgentWorkflow()
    return workflow.run(state)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a minimal single-agent baseline."""
    _init()
    try:
        state = _run_baseline(query)
        llm_client = LLMClient()
        console.print(
            Panel.fit(
                state.final_answer or "",
                title=f"Single-Agent Baseline ({llm_client.default_model})",
            )
        )
        if state.agent_results:
            meta = state.agent_results[0].metadata
            tokens_info = (
                f"[dim]Tokens: input={meta.get('input_tokens')}, "
                f"output={meta.get('output_tokens')}[/dim]"
            )
            console.print(tokens_info)
    except LabError as exc:
        console.print(Panel.fit(str(exc), title="Cấu hình API Key", style="yellow"))
        raise typer.Exit(code=1) from exc


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow."""
    _init()
    try:
        result = _run_multi_agent(query)
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc
    console.print(result.model_dump_json(indent=2))


@app.command("benchmark")
def benchmark(
    query: Annotated[
        str | None,
        typer.Option("--query", "-q", help="Specific query to benchmark"),
    ] = None,
    output_report: Annotated[
        str,
        typer.Option("--output", "-o", help="Output markdown report path"),
    ] = "reports/benchmark_report.md",
) -> None:
    """Run comparative benchmark between Single-Agent Baseline and Multi-Agent Workflow."""
    _init()
    queries = [query] if query else [
        "So sánh RAG truyền thống và GraphRAG trong hệ thống AI",
        "Phân tích ưu nhược điểm của kiến trúc Single-Agent vs Multi-Agent cho nghiên cứu",
    ]

    console.print(
        f"[bold cyan]🚀 Đang chạy Benchmark so sánh trên {len(queries)} câu hỏi...[/bold cyan]\n"
    )

    runners = {
        "Single-Agent Baseline": _run_baseline,
        "Multi-Agent Workflow": _run_multi_agent,
    }

    metrics = run_comparative_benchmark(queries, runners)

    # Render Table
    table = Table(
        title="📊 Kết quả Benchmark: Single-Agent vs Multi-Agent",
        header_style="bold magenta",
    )
    table.add_column("Hệ thống", style="cyan")
    table.add_column("Độ trễ (Latency)", justify="right")
    table.add_column("Chi phí (USD)", justify="right")
    table.add_column("Điểm chất lượng (0-10)", justify="right")
    table.add_column("Trích dẫn (Citation)", justify="right")
    table.add_column("Tỷ lệ lỗi (Failure)", justify="right")

    for m in metrics:
        cost = f"${m.estimated_cost_usd:.4f}" if m.estimated_cost_usd is not None else "N/A"
        qual = f"{m.quality_score:.1f}/10" if m.quality_score is not None else "N/A"
        cit = f"{m.citation_coverage:.0%}" if m.citation_coverage is not None else "0%"
        fail = f"{m.failure_rate:.0%}" if m.failure_rate is not None else "0%"
        table.add_row(m.run_name, f"{m.latency_seconds:.2f}s", cost, qual, cit, fail)

    console.print(table)

    # Save Markdown report
    report_content = render_markdown_report(metrics, sample_queries=queries)
    out_path = Path(output_report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_content, encoding="utf-8")
    console.print(f"\n[green]✅ Đã lưu báo cáo chi tiết tại: [bold]{output_report}[/bold][/green]")


if __name__ == "__main__":
    app()
