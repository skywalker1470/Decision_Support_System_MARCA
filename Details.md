# Multi-Agent Root Cause Analysis (RCA-Agents)

An orchestrator-worker multi-agent system that investigates GitHub issues by pulling evidence from tickets, source code, logs, and documentation, then produces a ranked, traceable root-cause hypothesis for human review.

This project is a scaled-down testbed for AI-agent support in industrial root cause analysis, similar in spirit to how engineering teams combine issue trackers, source repositories, and logs to diagnose faults in complex systems.

## Motivation

Engineers diagnosing an issue often have to manually stitch together evidence spread across a ticket, the codebase, CI logs, and documentation before forming a reliable hypothesis. This project explores whether a set of specialized AI agents, each responsible for one evidence type, can be orchestrated to assemble that evidence automatically and present a structured, auditable explanation instead of a black-box answer.

## Architecture

```
                     ┌─────────────────┐
                     │   Orchestrator   │
                     └────────┬─────────┘
        ┌──────────┬──────────┼──────────┬──────────┐
        ▼          ▼          ▼          ▼          ▼
   Ticket      Code       Log        Doc        (extendable)
   Agent       Agent      Agent      Agent
```

- **Ticket Agent** — retrieves similar past issues and defects via embedding search over issue history
- **Code Agent** — retrieves relevant source files or functions given an error message or stack trace
- **Log Agent** — parses CI/build logs for anomaly patterns tied to the issue
- **Doc Agent** — retrieves relevant sections from project documentation
- **Orchestrator** — combines agent outputs into a ranked root-cause hypothesis, with every claim linked back to its supporting evidence

## Data Sources

Public stand-ins for a real industrial toolchain (Dr MITRAC, Dimensions, SharePoint, GitLab, EWM):

| Evidence type | Source |
|---|---|
| Ticket history | GitHub Issues + comments |
| Source code | Repository files |
| Logs | CI/build logs, commit history |
| Documentation | README and docs folder |
| Work items | Linked pull requests |

## Tech Stack

- Python
- LangChain
- FAISS (vector retrieval)
- LLM via Ollama or an API backend
- LangGraph (or a lightweight custom router) for agent orchestration

## Evaluation

The system is evaluated on a held-out set of closed issues where the true root cause is known from the merged fix:

- **Correctness** — does the hypothesis match the known fix?
- **Completeness** — is all relevant evidence surfaced?
- **Traceability** — is every claim backed by a cited source?
- **Ablation** — comparing the full orchestrator against subsets of agents to identify which evidence types matter most

## Project Status

Work in progress. See `/notebooks` for experiments and `/report` for the write-up.

## Setup

```bash
git clone <repo-url>
cd rca-agents
python -m venv .venv
.venv\Scripts\activate      # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, set your Ollama endpoint/model and (optionally) a `GITHUB_TOKEN`
for higher API rate limits, then run:

```bash
python run_pipeline.py --issue owner/repo#123
# or
python run_pipeline.py --issue https://github.com/owner/repo/issues/123
```

To evaluate against a repo's closed-issue history:

```bash
python -m rca_agents.eval.run_eval --repo owner/repo --limit 20
```

## License

MIT