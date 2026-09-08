"""Builds a held-out eval set of closed issues where the true root cause is known
from the merged fix (the PR that closed the issue and the files it touched).
"""

from pydantic import BaseModel

from rca_agents.github_source import GithubSource


class EvalCase(BaseModel):
    issue_number: int
    issue_title: str
    fixing_pr_number: int
    fixed_files: list[str]


def build_eval_set(source: GithubSource, limit: int = 30, scan_limit: int = 300) -> list[EvalCase]:
    """Finds closed issues with a linked PR, using the PR's changed files as the
    ground-truth root-cause location.

    Recently-closed issues skew toward feature requests, duplicates, and other
    closures with no real fix, so a small `limit` against a large, active repo
    can starve this of cases. `scan_limit` controls how many closed issues get
    scanned (oldest closures included) to find `limit` usable ones.
    """
    cases: list[EvalCase] = []
    for issue in source.get_closed_issues(limit=scan_limit):
        if not issue.linked_pr_numbers:
            continue
        for pr_number in issue.linked_pr_numbers:
            try:
                files = source.get_pr_diff_files(pr_number)
            except Exception:
                continue
            if files:
                cases.append(
                    EvalCase(
                        issue_number=issue.number,
                        issue_title=issue.title,
                        fixing_pr_number=pr_number,
                        fixed_files=files,
                    )
                )
                break
        if len(cases) >= limit:
            break
    return cases
