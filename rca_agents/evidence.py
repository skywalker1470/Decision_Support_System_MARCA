from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """A single piece of evidence retrieved by an agent, traceable to its source."""

    source_type: str  # "ticket" | "code" | "log" | "doc"
    source_id: str  # e.g. issue #, file path, log line range, doc section
    content: str
    score: float = Field(default=0.0, description="Retrieval relevance score, higher is better")
    url: str | None = None


class AgentResult(BaseModel):
    agent_name: str
    items: list[EvidenceItem]
    summary: str = ""


class RootCauseHypothesis(BaseModel):
    rank: int
    claim: str
    confidence: float
    supporting_evidence: list[EvidenceItem]
