import json

from rca_agents.agents.code_agent import CodeAgent
from rca_agents.agents.doc_agent import DocAgent
from rca_agents.agents.log_agent import LogAgent
from rca_agents.agents.ticket_agent import TicketAgent
from rca_agents.evidence import AgentResult, EvidenceItem, RootCauseHypothesis
from rca_agents.github_source import GithubSource
from rca_agents.llm import get_chat_model

_SYSTEM_PROMPT = """You are a root-cause-analysis assistant. You are given a GitHub issue and \
evidence gathered by specialist agents (ticket history, source code, logs/commits, docs). \
Each evidence item has a source_id you must cite.

Produce a ranked list of root-cause hypotheses. Rules:
- Every claim must cite at least one evidence source_id that actually supports it.
- Do not invent evidence or source_ids that were not provided.
- Rank hypotheses by how well the evidence supports them, most likely first.
- If evidence is thin, say so plainly rather than fabricating a confident answer.

Respond ONLY with JSON matching this schema:
{
  "hypotheses": [
    {"claim": str, "confidence": float (0-1), "evidence_source_ids": [str, ...]}
  ]
}
"""


class Orchestrator:
    def __init__(self, repo_full_name: str):
        self.source = GithubSource(repo_full_name)
        self.ticket_agent = TicketAgent(self.source)
        self.code_agent = CodeAgent(self.source)
        self.log_agent = LogAgent(self.source)
        self.doc_agent = DocAgent(self.source)
        self.llm = get_chat_model()

    def investigate(self, issue_number: int) -> tuple[list[RootCauseHypothesis], list[AgentResult]]:
        issue = self.source.get_issue(issue_number)

        agent_results = [
            self.ticket_agent.run(issue),
            self.code_agent.run(issue.title, issue.body),
            self.log_agent.run(issue),
            self.doc_agent.run(issue.title, issue.body),
        ]

        all_items: dict[str, EvidenceItem] = {}
        for result in agent_results:
            for item in result.items:
                all_items[item.source_id] = item

        evidence_block = "\n\n".join(
            f"[{item.source_id}] ({item.source_type}, score={item.score:.2f})\n{item.content[:1500]}"
            for item in all_items.values()
        )

        user_prompt = (
            f"Issue #{issue.number}: {issue.title}\n\n{issue.body}\n\n"
            f"--- Evidence ---\n{evidence_block if evidence_block else '(no evidence retrieved)'}"
        )

        response = self.llm.invoke(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )

        hypotheses = self._parse_hypotheses(response.content, all_items)
        return hypotheses, agent_results

    def _parse_hypotheses(self, raw: str, all_items: dict[str, EvidenceItem]) -> list[RootCauseHypothesis]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text.split("\n", 1)[-1] if text.lower().startswith("json") else text

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return [
                RootCauseHypothesis(
                    rank=1,
                    claim=f"Model did not return valid JSON. Raw output: {raw[:500]}",
                    confidence=0.0,
                    supporting_evidence=[],
                )
            ]

        hypotheses = []
        for rank, h in enumerate(parsed.get("hypotheses", []), start=1):
            supporting = [all_items[sid] for sid in h.get("evidence_source_ids", []) if sid in all_items]
            hypotheses.append(
                RootCauseHypothesis(
                    rank=rank,
                    claim=h.get("claim", ""),
                    confidence=float(h.get("confidence", 0.0)),
                    supporting_evidence=supporting,
                )
            )
        return hypotheses
