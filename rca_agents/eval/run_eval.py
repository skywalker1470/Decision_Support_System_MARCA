"""Evaluates the orchestrator on a held-out set of closed issues.

Usage:
    python -m rca_agents.eval.run_eval --repo owner/name --limit 20
"""

import argparse
import statistics

from rich.console import Console
from rich.table import Table

from rca_agents.eval.dataset import build_eval_set
from rca_agents.eval.metrics import completeness, correctness, evidence_ids_from_items, traceability
from rca_agents.github_source import GithubSource
from rca_agents.orchestrator import Orchestrator

console = Console()


def run(repo: str, limit: int):
    source = GithubSource(repo)
    cases = build_eval_set(source, limit=limit)
    if not cases:
        console.print("[yellow]No eval cases found (no closed issues with a linked, mergeable PR).[/yellow]")
        return

    orchestrator = Orchestrator(repo)

    rows = []
    for case in cases:
        try:
            hypotheses, agent_results = orchestrator.investigate(case.issue_number)
        except Exception as e:
            console.print(f"[red]Skipping #{case.issue_number}: {e}[/red]")
            continue

        all_items = [item for r in agent_results for item in r.items]
        rows.append(
            {
                "issue": case.issue_number,
                "correctness": correctness(hypotheses, case),
                "completeness": completeness(hypotheses, case),
                "traceability": traceability(hypotheses, evidence_ids_from_items(all_items)),
            }
        )

    if not rows:
        console.print("[yellow]No cases could be evaluated.[/yellow]")
        return

    table = Table(title=f"RCA Eval — {repo} ({len(rows)} cases)")
    table.add_column("Issue")
    table.add_column("Correctness")
    table.add_column("Completeness")
    table.add_column("Traceability")
    for r in rows:
        table.add_row(f"#{r['issue']}", f"{r['correctness']:.2f}", f"{r['completeness']:.2f}", f"{r['traceability']:.2f}")
    console.print(table)

    console.print(
        f"\n[bold]Mean correctness:[/bold] {statistics.mean(r['correctness'] for r in rows):.3f}  "
        f"[bold]Mean completeness:[/bold] {statistics.mean(r['completeness'] for r in rows):.3f}  "
        f"[bold]Mean traceability:[/bold] {statistics.mean(r['traceability'] for r in rows):.3f}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    run(args.repo, args.limit)
