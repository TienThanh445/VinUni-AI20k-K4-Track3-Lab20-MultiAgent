import json
import logging
from pathlib import Path

import httpx

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


class SearchClient:
    """Provider-agnostic search client supporting Tavily API and local offline corpus."""

    def __init__(
        self,
        settings: Settings | None = None,
        api_key: str | None = None,
        corpus_dir: Path | str | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.api_key = (api_key or self.settings.tavily_api_key or "").strip() or None

        if corpus_dir:
            self.corpus_dir = Path(corpus_dir)
        else:
            self.corpus_dir = Path("ai_agent_offline_research_corpus_v2") / "topics"

    def _search_tavily(self, query: str, max_results: int) -> list[SourceDocument]:
        """Search using Tavily API."""
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            }
            with httpx.Client(timeout=self.settings.timeout_seconds) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

            results: list[SourceDocument] = []
            for item in data.get("results", []):
                results.append(
                    SourceDocument(
                        title=item.get("title", "Untitled Source"),
                        url=item.get("url"),
                        snippet=item.get("content", "").strip()[:500],
                        metadata={"score": item.get("score")},
                    )
                )
            if results:
                logger.info(f"Tavily search returned {len(results)} sources for '{query}'")
                return results[:max_results]
        except Exception as exc:
            logger.warning(f"Tavily search failed ({exc}), falling back to offline corpus.")
        return []

    def _search_offline_corpus(self, query: str, max_results: int) -> list[SourceDocument]:
        """Search in local offline corpus JSON files."""
        if not self.corpus_dir.exists():
            return []

        query_tokens = set(query.lower().replace("-", " ").replace("_", " ").split())
        scored_docs: list[tuple[float, SourceDocument]] = []

        try:
            for json_path in self.corpus_dir.glob("*.json"):
                with json_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                topic_info = data.get("topic", {})
                topic_name = topic_info.get("name", "")
                topic_tokens = set(topic_name.lower().split())
                score = len(query_tokens & topic_tokens)

                # Search articles in knowledge base
                kb = data.get("knowledge_base", {})
                for article in kb.get("knowledge_articles", []):
                    title = article.get("title", "")
                    content = article.get("content", "")
                    article_tokens = set(title.lower().split())
                    art_score = score + len(query_tokens & article_tokens) * 2
                    art_id = article.get("article_id", "art")

                    scored_docs.append(
                        (
                            art_score,
                            SourceDocument(
                                title=f"{topic_name}: {title}",
                                url=f"offline://corpus/{json_path.stem}/{art_id}",
                                snippet=content[:400].strip(),
                                metadata={"topic": topic_name, "article_id": art_id},
                            ),
                        )
                    )

            # Sort by score descending
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            return [doc for _, doc in scored_docs[:max_results]]
        except Exception as exc:
            logger.warning(f"Offline corpus search error: {exc}")
            return []

    def _fallback_mock(self, query: str, max_results: int) -> list[SourceDocument]:
        """Fallback mock documents when no search provider or corpus matches."""
        return [
            SourceDocument(
                title=f"Overview & Foundations: {query}",
                url="https://arxiv.org/abs/2402.01234",
                snippet=(
                    f"Comprehensive analysis of {query}. Multi-agent workflows decompose "
                    "research into specialized tasks (retrieval, analysis, synthesis), enhancing "
                    "grounding and reducing single-agent hallucination."
                ),
                metadata={"synthetic": True},
            ),
            SourceDocument(
                title=f"Architectural Trade-offs in {query}",
                url="https://arxiv.org/abs/2403.05678",
                snippet=(
                    "Evaluation of coordination cost, token latency, and quality tradeoffs. "
                    "Independent verification steps significantly improve citation precision."
                ),
                metadata={"synthetic": True},
            ),
            SourceDocument(
                title=f"State-of-the-art Practices and Benchmarks: {query}",
                url="https://arxiv.org/abs/2404.09012",
                snippet=(
                    "Empirical benchmarks demonstrate that specialized worker agents with "
                    "structured handoffs achieve superior factual accuracy over baselines."
                ),
                metadata={"synthetic": True},
            ),
        ][:max_results]

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query."""
        if self.api_key:
            tavily_results = self._search_tavily(query, max_results)
            if tavily_results:
                return tavily_results

        corpus_results = self._search_offline_corpus(query, max_results)
        if corpus_results:
            return corpus_results

        return self._fallback_mock(query, max_results)
