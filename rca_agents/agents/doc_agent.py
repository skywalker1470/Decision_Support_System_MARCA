"""Retrieves relevant sections from project documentation (README, /docs)."""

from rca_agents.evidence import AgentResult, EvidenceItem
from rca_agents.github_source import GithubSource
from rca_agents.retrieval import build_index, query_index


class DocAgent:
    name = "doc_agent"

    def __init__(self, source: GithubSource):
        self.source = source
        self._index = None

    def _ensure_index(self):
        if self._index is not None:
            return
        paths = self.source.list_docs()
        texts, metas = [], []
        for path in paths:
            try:
                f = self.source.get_file(path)
            except Exception:
                continue
            texts.append(f.content)
            metas.append({"path": path})
        self._index = build_index(texts, metas) if texts else None

    def run(self, issue_title: str, issue_body: str, k: int = 4) -> AgentResult:
        self._ensure_index()
        items: list[EvidenceItem] = []
        if self._index is not None:
            query_text = f"{issue_title}\n\n{issue_body}"
            for doc, score in query_index(self._index, query_text, k=k):
                items.append(
                    EvidenceItem(
                        source_type="doc",
                        source_id=doc.metadata["path"],
                        content=doc.page_content,
                        score=1.0 / (1.0 + score),
                    )
                )

        summary = f"Found {len(items)} relevant documentation section(s)." if items else "No relevant documentation found."
        return AgentResult(agent_name=self.name, items=items, summary=summary)
