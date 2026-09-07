# Multi-Agent Root Cause Analysis (RCA-Agents)

An orchestrator-worker multi-agent system that investigates GitHub issues by pulling evidence from tickets, source code, logs, and documentation, then produces a ranked, traceable root-cause hypothesis for human review.

This project is a scaled-down testbed for AI-agent support in industrial root cause analysis, similar in spirit to how engineering teams combine issue trackers, source repositories, and logs to diagnose faults in complex systems.

## Motivation

Engineers diagnosing an issue often have to manually stitch together evidence spread across a ticket, the codebase, CI logs, and documentation before forming a reliable hypothesis. This project explores whether a set of specialized AI agents, each responsible for one evidence type, can be orchestrated to assemble that evidence automatically and present a structured, auditable explanation instead of a black-box answer.

## Architecture

```
                     +-----------------+
                     |   Orchestrator   |
                     +--------+---------+
        +----------+----------+----------+----------+
        |          |          |          |          |
     Ticket      Code       Log        Doc        (extendable)
     Agent       Agent      Agent      Agent
```

- **Ticket Agent** retrieves similar past issues and defects via embedding search over issue history
- **Code Agent** retrieves relevant source files or functions given an error message or stack trace
- **Log Agent** parses CI/build logs and commit history for anomaly patterns tied to the issue
- **Doc Agent** retrieves relevant sections from project documentation
- **Orchestrator** combines agent outputs into a ranked, cited root-cause hypothesis, with every claim linked back to its supporting evidence

## Data Sources

Public stand-ins for a real industrial toolchain (Dr MITRAC, Dimensions, SharePoint, GitLab, EWM):

| Evidence type | Source |
|---|---|
| Ticket history | GitHub Issues and comments |
| Source code | Repository files |
| Logs | Error/traceback text in issues, commit history |
| Documentation | README and docs folder |
| Work items | Linked pull requests |

## Tech Stack

- Python 3.11+
- LangChain, langchain-text-splitters
- FAISS (vector retrieval)
- Ollama (local LLM and embeddings)
- PyGithub for GitHub API access

## Project Layout

```
rca_agents/
  agents/
    ticket_agent.py    similar-issue retrieval
    code_agent.py       source file retrieval, stack trace parsing
    log_agent.py         error/log snippet and commit signal extraction
    doc_agent.py         documentation retrieval
  eval/
    dataset.py           builds a held-out eval set from closed issues + linked PRs
    metrics.py           correctness, completeness, traceability
    run_eval.py           eval CLI
  config.py               settings loaded from .env
  evidence.py              shared data models (EvidenceItem, AgentResult, RootCauseHypothesis)
  llm.py                    Ollama chat and embedding clients
  github_source.py          GitHub API wrapper (issues, files, commits, PRs)
  retrieval.py               FAISS index build/query helpers
  orchestrator.py             ties the agents together and calls the LLM for the final ranking
run_pipeline.py                CLI entrypoint
```

## Setup

```bash
git clone <repo-url>
cd rca-agents
python -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Pull the local models with Ollama:

```bash
ollama pull llama3.1
ollama pull nomic-embed-text
```

Copy `.env.example` to `.env` and set a `GITHUB_TOKEN`. A token is effectively required: unauthenticated GitHub API access is capped at 60 requests/hour, which the ticket, code, and doc agents burn through almost immediately when indexing a repo. A classic personal access token with no scopes selected is enough for public repos. Generate one at https://github.com/settings/tokens and raises the limit to 5,000/hour.

```
GITHUB_TOKEN=ghp_your_token_here
```

Never commit `.env` or paste a token into chat, a PR, or an issue. `.env` is already gitignored.

## Usage

```bash
python run_pipeline.py --issue owner/repo#123
# or
python run_pipeline.py --issue https://github.com/owner/repo/issues/123
```

Example, tested against a real closed issue in `psf/requests`:

```bash
python run_pipeline.py --issue psf/requests#7605
```

This prints a summary from each of the four agents, followed by a ranked list of hypotheses, each with a confidence score and the evidence source IDs (file paths, issue numbers, commit SHAs) that support it.

## Evaluation

The system is evaluated on a held-out set of closed issues where the true root cause is known from the merged fix (the PR that closed the issue and the files it changed):

- **Correctness**: does the top hypothesis cite at least one of the files actually touched by the fix?
- **Completeness**: what fraction of the actually-fixed files show up as cited evidence anywhere across all hypotheses?
- **Traceability**: what fraction of cited evidence source IDs correspond to evidence that was actually retrieved, rather than fabricated?
- **Ablation** (planned): comparing the full orchestrator against subsets of agents to identify which evidence types matter most

Run it against a repo's closed-issue history:

```bash
python -m rca_agents.eval.run_eval --repo owner/repo --limit 20
```

## Known Limitations

- With a single local 8B model, the orchestrator sometimes produces multiple hypotheses that restate the same underlying claim in slightly different words rather than consolidating them. A dedup/merge pass is a natural next step.
- The log agent has no generic CI-log API to draw from across arbitrary repos, so it works off error text pasted into the issue itself plus recent commit messages as a proxy signal, rather than real CI logs.
- Retrieval quality depends on `nomic-embed-text` embeddings and a fixed chunking strategy; larger repositories will need smarter chunking or file filtering to stay fast.

## Project Status

Work in progress. See `/notebooks` for experiments and `/report` for the write-up.

## License

MIT
