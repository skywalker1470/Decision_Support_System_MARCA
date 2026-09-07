"""Retrieves relevant source files/functions given an error message or stack trace."""

import re

from rca_agents.evidence import AgentResult, EvidenceItem
from rca_agents.github_source import GithubSource
from rca_agents.retrieval import build_index, query_index

_STACK_FRAME_RE = re.compile(r'File "([^"]+)"|at .*\(([^:)]+):\d+')


class CodeAgent:
    name = "code_agent"

    def __init__(self, source: GithubSource, max_files: int = 150):
        self.source = source
        self.max_files = max_files
        self._index = None

    def _ensure_index(self):
        if self._index is not None:
            return
        paths = self.source.list_source_files()[: self.max_files]
        texts, metas = [], []
        for path in paths:
            try:
                f = self.source.get_file(path)
            except Exception:
                continue
            texts.append(f.content)
            metas.append({"path": path})
        self._index = build_index(texts, metas) if texts else None

    def _extract_hinted_paths(self, error_text: str) -> list[str]:
        hints = set()
        for m in _STACK_FRAME_RE.finditer(error_text):
            path = m.group(1) or m.group(2)
            if path:
                hints.add(path)
        return list(hints)

    def run(self, issue_title: str, issue_body: str, k: int = 5) -> AgentResult:
        self._ensure_index()
        query_text = f"{issue_title}\n\n{issue_body}"
        items: list[EvidenceItem] = []

        for hinted_path in self._extract_hinted_paths(issue_body):
            try:
                f = self.source.get_file(hinted_path)
                items.append(
                    EvidenceItem(
                        source_type="code",
                        source_id=hinted_path,
                        content=f.content[:3000],
                        score=1.0,
                    )
                )
            except Exception:
                continue

        if self._index is not None:
            for doc, score in query_index(self._index, query_text, k=k):
                path = doc.metadata["path"]
                if any(it.source_id == path for it in items):
                    continue
                items.append(
                    EvidenceItem(
                        source_type="code",
                        source_id=path,
                        content=doc.page_content,
                        score=1.0 / (1.0 + score),
                    )
                )

        summary = f"Found {len(items)} candidate source file(s)." if items else "No relevant source files found."
        return AgentResult(agent_name=self.name, items=items, summary=summary)
