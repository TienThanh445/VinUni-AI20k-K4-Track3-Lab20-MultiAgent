import re
from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def compute_citation_coverage(state: ResearchState) -> float:
    """Calculate the ratio of sources referenced in the final answer."""
    if not state.sources or not state.final_answer:
        return 0.0

    cited_count = 0
    answer_text = state.final_answer.lower()

    for idx, source in enumerate(state.sources, start=1):
        # Match citation patterns like [1], [2] or source title snippets
        citation_pattern = rf"\[{idx}\]"
        title_snippet = source.title.lower()[:25]

        if re.search(citation_pattern, state.final_answer) or (
            len(title_snippet) > 5 and title_snippet in answer_text
        ):
            cited_count += 1

    return min(1.0, cited_count / len(state.sources))


def estimate_token_cost(state: ResearchState) -> float:
    """Estimate USD cost across all agent steps."""
    settings = get_settings()
    total_in = 0
    total_out = 0

    for result in state.agent_results:
        meta = result.metadata or {}
        total_in += int(meta.get("input_tokens") or 0)
        total_out += int(meta.get("output_tokens") or 0)

    # Groq free tier is effectively 0.0 USD
    if settings.groq_api_key:
        return 0.0

    # OpenAI gpt-4o-mini pricing baseline: $0.15 / 1M in, $0.60 / 1M out
    cost = (total_in / 1_000_000) * 0.150 + (total_out / 1_000_000) * 0.600
    return round(cost, 5)


def compute_quality_score(state: ResearchState) -> float:
    """Evaluate response quality on a 0-10 scale based on completeness, structure, and grounding."""
    if not state.final_answer or len(state.final_answer.strip()) == 0:
        return 0.0

    score = 3.0
    text = state.final_answer

    # Length and depth check
    if len(text) >= 1000:
        score += 1.5
    elif len(text) >= 500:
        score += 1.0

    # Structured formatting (headings, bullet points)
    if "#" in text and ("-" in text or "*" in text):
        score += 1.5

    # Grounding & citation presence
    if re.search(r"\[\d+\]", text) or "references" in text.lower():
        score += 2.0

    # Analytical depth keywords
    analytical_keywords = ["trade-off", "so sánh", "ưu điểm", "nhược điểm", "hạn chế", "synthesis"]
    if any(kw in text.lower() for kw in analytical_keywords):
        score += 1.0

    # Evidence quantity
    if len(state.sources) >= 3:
        score += 1.0

    # Error penalties
    if state.errors:
        score = max(0.0, score - 2.0 * len(state.errors))

    return min(10.0, round(score, 1))


def run_benchmark(
    run_name: str, query: str, runner: Runner
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Execute a runner on a query and calculate comprehensive benchmark metrics."""
    started = perf_counter()
    try:
        state = runner(query)
        failure_rate = 1.0 if state.errors else 0.0
    except Exception as exc:
        state = ResearchState(
            request={"query": query},  # type: ignore[arg-type]
            errors=[f"Runner exception: {exc}"],
        )
        failure_rate = 1.0

    latency = perf_counter() - started
    citation_cov = compute_citation_coverage(state)
    cost = estimate_token_cost(state)
    quality = compute_quality_score(state)

    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=round(latency, 2),
        estimated_cost_usd=cost,
        quality_score=quality,
        citation_coverage=round(citation_cov, 2),
        failure_rate=failure_rate,
        notes=f"Processed query with {len(state.sources)} sources",
    )
    return state, metrics


def run_comparative_benchmark(
    queries: list[str], runners: dict[str, Runner]
) -> list[BenchmarkMetrics]:
    """Run benchmark queries across multiple systems and aggregate metrics."""
    aggregated: list[BenchmarkMetrics] = []

    for name, runner in runners.items():
        total_lat = 0.0
        total_cost = 0.0
        total_qual = 0.0
        total_cov = 0.0
        total_fail = 0.0

        for q in queries:
            _, m = run_benchmark(name, q, runner)
            total_lat += m.latency_seconds
            total_cost += m.estimated_cost_usd or 0.0
            total_qual += m.quality_score or 0.0
            total_cov += m.citation_coverage or 0.0
            total_fail += m.failure_rate or 0.0

        n = len(queries) or 1
        aggregated.append(
            BenchmarkMetrics(
                run_name=name,
                latency_seconds=round(total_lat / n, 2),
                estimated_cost_usd=round(total_cost / n, 5),
                quality_score=round(total_qual / n, 1),
                citation_coverage=round(total_cov / n, 2),
                failure_rate=round(total_fail / n, 2),
                notes=f"Averaged over {n} queries",
            )
        )

    return aggregated
