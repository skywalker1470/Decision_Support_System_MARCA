"""Retrieves similar past issues/defects via embedding search over issue history."""

from rca_agents.evidence import AgentResult, EvidenceItem
from rca_agents.github_source import GithubSource, TicketRecord
from rca_agents.retrieval import build_index, query_index


class TicketAgent:
    name = "ticket_agent"

    def __init__(self, source: GithubSource, history_limit: int = 200):
        self.source = source
        self.history_limit = history_limit
        self._index = None
        self._issues_by_number: dict[int, TicketRecord] = {}

    def _ensure_index(self):
        if self._index is not None:
            return
        issues = self.source.get_closed_issues(limit=self.history_limit)
        self._issues_by_number = {i.number: i for i in issues}
        texts, metas = [], []
        for issue in issues:
            text = f"{issue.title}\n\n{issue.body}\n\n" + "\n".join(issue.comments)
            texts.append(text)
            metas.append({"number": issue.number, "title": issue.title, "url": issue.url})
        self._index = build_index(texts, metas)

    def run(self, current_issue: TicketRecord, k: int = 5) -> AgentResult:
        self._ensure_index()
        query = f"{current_issue.title}\n\n{current_issue.body}"
        results = query_index(self._index, query, k=k)

        items = []
        for doc, score in results:
            number = doc.metadata["number"]
            if number == current_issue.number:
                continue
            items.append(
                EvidenceItem(
                    source_type="ticket",
                    source_id=f"#{number}",
                    content=doc.page_content,
                    score=1.0 / (1.0 + score),
                    url=doc.metadata.get("url"),
                )
            )

        summary = f"Found {len(items)} similar historical issue(s)." if items else "No similar historical issues found."
        return AgentResult(agent_name=self.name, items=items, summary=summary)
