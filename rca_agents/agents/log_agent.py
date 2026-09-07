"""Parses CI/build logs and commit history for anomaly patterns tied to the issue.

No generic public CI-log API exists across repos, so this agent works off:
  1. Log/traceback text pasted directly into the issue body or comments.
  2. Recent commit messages around the issue's timeframe, as a lightweight proxy
     for "what changed recently that could explain this."
"""

import re

from rca_agents.evidence import AgentResult, EvidenceItem
from rca_agents.github_source import GithubSource, TicketRecord

_ERROR_LINE_RE = re.compile(
    r"(?im)^.*(error|exception|traceback|panic|fatal|fail(ed|ure)?).*$"
)
_CODE_BLOCK_RE = re.compile(r"```(?:\w*\n)?(.*?)```", re.DOTALL)


class LogAgent:
    name = "log_agent"

    def __init__(self, source: GithubSource, recent_commits: int = 30):
        self.source = source
        self.recent_commits = recent_commits

    def _extract_log_snippets(self, text: str) -> list[str]:
        snippets = []
        for block in _CODE_BLOCK_RE.findall(text):
            if _ERROR_LINE_RE.search(block):
                snippets.append(block.strip())
        if not snippets:
            lines = _ERROR_LINE_RE.findall(text)
            # findall with groups returns tuples; re-search raw lines instead
            for line in text.splitlines():
                if _ERROR_LINE_RE.match(line):
                    snippets.append(line.strip())
        return snippets

    def _recent_commit_messages(self) -> list[tuple[str, str]]:
        commits = self.source.repo.get_commits()[: self.recent_commits]
        return [(c.sha[:7], c.commit.message.splitlines()[0]) for c in commits]

    def run(self, issue: TicketRecord) -> AgentResult:
        items: list[EvidenceItem] = []
        full_text = issue.body + "\n" + "\n".join(issue.comments)

        for i, snippet in enumerate(self._extract_log_snippets(full_text)):
            items.append(
                EvidenceItem(
                    source_type="log",
                    source_id=f"issue-log-{i}",
                    content=snippet[:2000],
                    score=1.0,
                )
            )

        try:
            for sha, message in self._recent_commit_messages():
                if _ERROR_LINE_RE.search(message) or "fix" in message.lower():
                    items.append(
                        EvidenceItem(
                            source_type="log",
                            source_id=f"commit-{sha}",
                            content=message,
                            score=0.5,
                        )
                    )
        except Exception:
            pass

        summary = f"Extracted {len(items)} log/commit signal(s)." if items else "No log or commit signals found."
        return AgentResult(agent_name=self.name, items=items, summary=summary)
