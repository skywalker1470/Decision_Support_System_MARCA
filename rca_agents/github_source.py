"""Thin wrapper around PyGithub for pulling issues, comments, PRs, and repo files."""

import base64
from dataclasses import dataclass

from github import Github
from github.Repository import Repository

from rca_agents.config import settings


@dataclass
class TicketRecord:
    number: int
    title: str
    body: str
    comments: list[str]
    state: str
    url: str
    linked_pr_numbers: list[int]


@dataclass
class RepoFile:
    path: str
    content: str


class GithubSource:
    def __init__(self, repo_full_name: str):
        token = settings.github_token or None
        self._gh = Github(token) if token else Github()
        self.repo: Repository = self._gh.get_repo(repo_full_name)

    def get_issue(self, number: int) -> TicketRecord:
        issue = self.repo.get_issue(number)
        comments = [c.body for c in issue.get_comments() if c.body]
        linked_prs = self._find_linked_prs(issue.body or "", comments)
        return TicketRecord(
            number=issue.number,
            title=issue.title,
            body=issue.body or "",
            comments=comments,
            state=issue.state,
            url=issue.html_url,
            linked_pr_numbers=linked_prs,
        )

    def get_closed_issues(self, limit: int = 200) -> list[TicketRecord]:
        records = []
        for issue in self.repo.get_issues(state="closed")[:limit]:
            if issue.pull_request is not None:
                continue
            comments = [c.body for c in issue.get_comments() if c.body]
            records.append(
                TicketRecord(
                    number=issue.number,
                    title=issue.title,
                    body=issue.body or "",
                    comments=comments,
                    state=issue.state,
                    url=issue.html_url,
                    linked_pr_numbers=self._find_linked_prs(issue.body or "", comments),
                )
            )
        return records

    def _find_linked_prs(self, body: str, comments: list[str]) -> list[int]:
        import re

        text = body + " " + " ".join(comments)
        return sorted({int(n) for n in re.findall(r"#(\d+)", text)})

    def list_source_files(self, extensions: tuple[str, ...] = (".py", ".js", ".ts", ".go", ".java")) -> list[str]:
        paths = []
        contents = self.repo.get_contents("")
        while contents:
            item = contents.pop(0)
            if item.type == "dir":
                contents.extend(self.repo.get_contents(item.path))
            elif item.path.endswith(extensions):
                paths.append(item.path)
        return paths

    def get_file(self, path: str) -> RepoFile:
        f = self.repo.get_contents(path)
        content = base64.b64decode(f.content).decode("utf-8", errors="replace")
        return RepoFile(path=path, content=content)

    def get_pr_diff_files(self, pr_number: int) -> list[str]:
        pr = self.repo.get_pull(pr_number)
        return [f.filename for f in pr.get_files()]

    def list_docs(self) -> list[str]:
        paths = []
        contents = self.repo.get_contents("")
        while contents:
            item = contents.pop(0)
            if item.type == "dir":
                contents.extend(self.repo.get_contents(item.path))
            elif item.path.lower().endswith(".md"):
                paths.append(item.path)
        return paths
