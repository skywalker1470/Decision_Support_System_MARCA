from rca_agents.eval.dataset import EvalCase
from rca_agents.evidence import EvidenceItem, RootCauseHypothesis


def correctness(hypotheses: list[RootCauseHypothesis], case: EvalCase) -> float:
    """1.0 if the top hypothesis cites at least one of the actually-fixed files."""
    if not hypotheses:
        return 0.0
    top = hypotheses[0]
    cited_paths = {e.source_id for e in top.supporting_evidence if e.source_type == "code"}
    return 1.0 if cited_paths & set(case.fixed_files) else 0.0


def completeness(hypotheses: list[RootCauseHypothesis], case: EvalCase) -> float:
    """Fraction of the actually-fixed files that appear as cited evidence anywhere
    across all hypotheses.
    """
    if not case.fixed_files:
        return 0.0
    cited_paths = {
        e.source_id
        for h in hypotheses
        for e in h.supporting_evidence
        if e.source_type == "code"
    }
    hit = cited_paths & set(case.fixed_files)
    return len(hit) / len(case.fixed_files)


def traceability(hypotheses: list[RootCauseHypothesis], all_evidence_ids: set[str]) -> float:
    """Fraction of cited evidence source_ids that actually existed in the retrieved
    evidence pool (i.e. nothing was fabricated).
    """
    cited = [e.source_id for h in hypotheses for e in h.supporting_evidence]
    if not cited:
        return 1.0
    valid = sum(1 for sid in cited if sid in all_evidence_ids)
    return valid / len(cited)


def evidence_ids_from_items(items: list[EvidenceItem]) -> set[str]:
    return {i.source_id for i in items}
