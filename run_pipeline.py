import argparse
import re
import sys

from rich.console import Console
from rich.panel import Panel

from rca_agents.orchestrator import Orchestrator

console = Console()


def parse_issue_ref(ref: str) -> tuple[str, int]:
    """Accepts 'owner/repo#123' or a full GitHub issue URL."""
    url_match = re.match(r"https?://github\.com/([^/]+/[^/]+)/issues/(\d+)", ref)
    if url_match:
        return url_match.group(1), int(url_match.group(2))

    shorthand_match = re.match(r"([^/]+/[^#]+)#(\d+)", ref)
    if shorthand_match:
        return shorthand_match.group(1), int(shorthand_match.group(2))

    raise ValueError(f"Could not parse issue reference: {ref!r}. Use 'owner/repo#123' or a GitHub issue URL.")


def main():
    parser = argparse.ArgumentParser(description="Multi-agent root cause analysis over a GitHub issue.")
    parser.add_argument("--issue", required=True, help="e.g. 'octocat/hello-world#42' or a GitHub issue URL")
    args = parser.parse_args()

    try:
        repo_full_name, issue_number = parse_issue_ref(args.issue)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    console.print(f"[bold]Investigating[/bold] {repo_full_name}#{issue_number} ...")

    orchestrator = Orchestrator(repo_full_name)
    hypotheses, agent_results = orchestrator.investigate(issue_number)

    for result in agent_results:
        console.print(f"[dim]{result.agent_name}: {result.summary}[/dim]")

    console.print()
    if not hypotheses:
        console.print("[yellow]No hypotheses generated.[/yellow]")
        return

    for h in hypotheses:
        evidence_lines = "\n".join(f"  - [{e.source_type}] {e.source_id}" for e in h.supporting_evidence) or "  (none)"
        body = f"{h.claim}\n\nConfidence: {h.confidence:.2f}\nEvidence:\n{evidence_lines}"
        console.print(Panel(body, title=f"#{h.rank} hypothesis", border_style="cyan"))


if __name__ == "__main__":
    main()
