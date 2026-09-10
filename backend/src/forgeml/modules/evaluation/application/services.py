from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from forgeml.modules.evaluation.domain.entities import (
    EVALUATION_COMPARISON_SCHEMA_VERSION,
    EvaluationApprovalChecklistItem,
    EvaluationCandidate,
    EvaluationComparisonSummary,
    EvaluationLeaderboardEntry,
    EvaluationMetricSlice,
    EvaluationModelCard,
    EvaluationModelEvidence,
    EvaluationModelMetric,
)
from forgeml.modules.evaluation.repositories.interfaces import (
    EvaluationComparisonRepository,
)
from forgeml.platform.domain.errors import PermissionDeniedError, ResourceNotFoundError
from forgeml.platform.security.rbac import Principal

_PRIMARY_METRIC_PRIORITY = (
    "auc",
    "roc_auc",
    "accuracy",
    "f1",
    "ndcg_at_10",
    "ndcg_at_k",
    "map_at_10",
    "mrr_at_10",
    "recall_at_5",
    "precision_at_1_percent",
    "precision",
    "recall",
    "coverage",
    "embedding_coverage",
    "log_loss",
    "rmse",
    "mae",
    "mse",
    "latency_ms",
    "error_rate",
)
_LOWER_IS_BETTER_TOKENS = ("loss", "error", "latency", "rmse", "mae", "mse")


@dataclass(frozen=True)
class GetEvaluationComparisonQuery:
    organization_id: UUID
    project_id: UUID


class EvaluationComparisonService:
    def __init__(self, *, repository: EvaluationComparisonRepository) -> None:
        self._repository = repository

    def get_evaluation_comparison_summary(
        self,
        query: GetEvaluationComparisonQuery,
        principal: Principal,
    ) -> EvaluationComparisonSummary:
        if not principal.has("evaluation:read"):
            raise PermissionDeniedError(
                "You do not have permission to read evaluation comparisons."
            )
        if str(query.organization_id) != principal.organization_id:
            raise PermissionDeniedError(
                "You cannot read evaluation comparisons for another organization."
            )

        snapshot = self._repository.load_snapshot(
            query.organization_id,
            query.project_id,
        )
        if snapshot is None:
            raise ResourceNotFoundError("Project was not found.")

        primary_metric_name = _select_primary_metric(snapshot.candidates)
        higher_is_better = (
            _higher_is_better(primary_metric_name) if primary_metric_name else True
        )
        leaderboard = _build_leaderboard(
            snapshot.candidates,
            primary_metric_name,
            higher_is_better,
        )
        recommended_run_id = (
            leaderboard[0].experiment_run_id if leaderboard and primary_metric_name else None
        )
        model_cards = _build_model_cards(snapshot.model_evidence, primary_metric_name)
        approval_checklist = _build_approval_checklist(
            snapshot.candidates,
            model_cards,
            recommended_run_id,
        )
        return EvaluationComparisonSummary(
            schema_version=EVALUATION_COMPARISON_SCHEMA_VERSION,
            project_id=snapshot.project_id,
            project_name=snapshot.project_name,
            project_slug=snapshot.project_slug,
            project_status=snapshot.project_status,
            primary_metric_name=primary_metric_name,
            higher_is_better=higher_is_better,
            candidate_count=len(snapshot.candidates),
            recommended_experiment_run_id=recommended_run_id,
            leaderboard=leaderboard,
            metric_slices=_build_metric_slices(snapshot.candidates),
            model_cards=model_cards,
            approval_checklist=approval_checklist,
            narrative=_build_narrative(
                snapshot.candidates,
                leaderboard,
                model_cards,
                approval_checklist,
            ),
            generated_at=datetime.now(UTC),
        )


def _select_primary_metric(
    candidates: tuple[EvaluationCandidate, ...],
) -> str | None:
    objective_names: list[str] = []
    for candidate in candidates:
        if (
            candidate.objective_metric_name
            and candidate.objective_metric_name in candidate.metrics
            and candidate.objective_metric_name not in objective_names
        ):
            objective_names.append(candidate.objective_metric_name)
    if objective_names:
        return objective_names[0]

    metric_names = {
        metric_name
        for candidate in candidates
        for metric_name in candidate.metrics
        if _metric_value(candidate, metric_name) is not None
    }
    for metric_name in _PRIMARY_METRIC_PRIORITY:
        if metric_name in metric_names:
            return metric_name
    return sorted(metric_names)[0] if metric_names else None


def _build_leaderboard(
    candidates: tuple[EvaluationCandidate, ...],
    primary_metric_name: str | None,
    higher_is_better: bool,
) -> tuple[EvaluationLeaderboardEntry, ...]:
    ranked_candidates = tuple(
        sorted(
            candidates,
            key=lambda candidate: _candidate_sort_key(
                candidate,
                primary_metric_name,
                higher_is_better,
            ),
        )
    )
    baseline_value = _baseline_value(candidates, primary_metric_name, higher_is_better)
    entries: list[EvaluationLeaderboardEntry] = []
    for rank, candidate in enumerate(ranked_candidates, start=1):
        metric_value = _metric_value(candidate, primary_metric_name)
        entries.append(
            EvaluationLeaderboardEntry(
                rank=rank,
                experiment_run_id=candidate.experiment_run_id,
                run_name=candidate.run_name,
                experiment_name=candidate.experiment_name,
                status=candidate.status,
                model_type=candidate.model_type,
                primary_metric_name=primary_metric_name,
                primary_metric_value=metric_value,
                delta_from_baseline=_delta_from_baseline(
                    metric_value,
                    baseline_value,
                    higher_is_better,
                ),
                quality_score=_quality_score(candidate),
                model_version_label=_model_version_label(candidate),
                approval_status=candidate.approval_status,
                evidence_summary=_evidence_summary(candidate),
            )
        )
    return tuple(entries)


def _build_metric_slices(
    candidates: tuple[EvaluationCandidate, ...],
) -> tuple[EvaluationMetricSlice, ...]:
    metric_names = sorted(
        {
            metric_name
            for candidate in candidates
            for metric_name in candidate.metrics
            if _metric_value(candidate, metric_name) is not None
        },
        key=_metric_sort_key,
    )
    slices: list[EvaluationMetricSlice] = []
    for metric_name in metric_names:
        higher_is_better = _higher_is_better(metric_name)
        candidate_values = [
            (candidate, value)
            for candidate in candidates
            if (value := _metric_value(candidate, metric_name)) is not None
        ]
        if not candidate_values:
            continue
        best_candidate, best_value = sorted(
            candidate_values,
            key=lambda item: -item[1] if higher_is_better else item[1],
        )[0]
        values = [value for _, value in candidate_values]
        baseline_value = min(values) if higher_is_better else max(values)
        slices.append(
            EvaluationMetricSlice(
                metric_name=metric_name,
                candidate_count=len(candidate_values),
                best_value=best_value,
                baseline_value=baseline_value,
                delta_from_baseline=_delta_from_baseline(
                    best_value,
                    baseline_value,
                    higher_is_better,
                )
                or 0.0,
                best_experiment_run_id=best_candidate.experiment_run_id,
                best_run_name=best_candidate.run_name,
                higher_is_better=higher_is_better,
            )
        )
    return tuple(slices)


def _build_model_cards(
    model_evidence: tuple[EvaluationModelEvidence, ...],
    primary_metric_name: str | None,
) -> tuple[EvaluationModelCard, ...]:
    sorted_evidence = sorted(
        model_evidence,
        key=lambda evidence: (
            0 if evidence.approval_status == "approved" else 1,
            -evidence.version,
            evidence.registered_model_name,
        ),
    )
    return tuple(
        EvaluationModelCard(
            model_version_id=evidence.model_version_id,
            model_name=evidence.registered_model_name,
            version=evidence.version,
            status=evidence.status,
            approval_status=evidence.approval_status,
            model_format=evidence.model_format,
            metric_summary=_metric_summary(evidence.metrics, primary_metric_name),
            signature_summary=_signature_summary(evidence.signature),
            artifact_uri=evidence.artifact_uri,
            artifact_manifest_uri=evidence.artifact_manifest_uri,
            artifact_manifest_hash=evidence.artifact_manifest_hash,
            lineage_summary=evidence.lineage_sources
            or (
                f"training_run:{evidence.training_run_id}",
                f"experiment_run:{evidence.experiment_run_id}",
            ),
            risk_flags=_risk_flags(evidence),
        )
        for evidence in sorted_evidence
    )


def _build_approval_checklist(
    candidates: tuple[EvaluationCandidate, ...],
    model_cards: tuple[EvaluationModelCard, ...],
    recommended_run_id: UUID | None,
) -> tuple[EvaluationApprovalChecklistItem, ...]:
    if recommended_run_id is None:
        return (
            EvaluationApprovalChecklistItem(
                key="candidate",
                label="Evaluation candidate",
                status="missing",
                detail="No scored experiment run is available yet.",
                evidence="Create or complete a training run with logged metrics.",
            ),
        )

    candidate = next(
        item for item in candidates if item.experiment_run_id == recommended_run_id
    )
    model_card = next(
        (
            item
            for item in model_cards
            if item.model_version_id == candidate.model_version_id
        ),
        None,
    )
    return (
        EvaluationApprovalChecklistItem(
            key="offline_metrics",
            label="Offline metrics",
            status="passed" if candidate.metrics else "missing",
            detail=(
                f"{len(candidate.metrics)} metrics are attached to the candidate run."
                if candidate.metrics
                else "The candidate does not expose offline metrics."
            ),
            evidence=candidate.run_name,
        ),
        EvaluationApprovalChecklistItem(
            key="evaluation_report",
            label="Evaluation report",
            status="passed" if candidate.evaluation_report else "missing",
            detail=(
                "Evaluation report metadata is attached to the run."
                if candidate.evaluation_report
                else "Attach an evaluation report before review."
            ),
            evidence=candidate.artifact_uri or "experiment run metadata",
        ),
        EvaluationApprovalChecklistItem(
            key="lineage",
            label="Dataset and feature lineage",
            status=(
                "passed"
                if candidate.dataset_version_id or candidate.feature_set_id
                else "missing"
            ),
            detail=(
                "The candidate links to reproducible dataset or feature inputs."
                if candidate.dataset_version_id or candidate.feature_set_id
                else "Register dataset or feature lineage before approval."
            ),
            evidence=_lineage_evidence(candidate),
        ),
        EvaluationApprovalChecklistItem(
            key="artifact_manifest",
            label="Artifact manifest",
            status=_model_card_status(model_card, "artifact_manifest_hash"),
            detail=(
                "A manifest URI and checksum are available."
                if model_card and model_card.artifact_manifest_hash
                else "Promote a model version with a manifest URI and checksum."
            ),
            evidence=model_card.artifact_manifest_uri if model_card else "model registry",
        ),
        EvaluationApprovalChecklistItem(
            key="model_signature",
            label="Model signature",
            status="passed"
            if model_card and model_card.signature_summary
            else "warning"
            if model_card
            else "missing",
            detail=(
                ", ".join(model_card.signature_summary)
                if model_card and model_card.signature_summary
                else "Capture model inputs and outputs before production review."
            ),
            evidence=model_card.model_format if model_card else "model registry",
        ),
        EvaluationApprovalChecklistItem(
            key="approval",
            label="Reviewer approval",
            status="passed"
            if candidate.approval_status == "approved"
            else "warning"
            if candidate.model_version_id
            else "missing",
            detail=(
                "The recommended model version is approved."
                if candidate.approval_status == "approved"
                else "The model version still needs reviewer approval."
                if candidate.model_version_id
                else "Promote the run before reviewer approval."
            ),
            evidence=_model_version_label(candidate) or "not promoted",
        ),
    )


def _build_narrative(
    candidates: tuple[EvaluationCandidate, ...],
    leaderboard: tuple[EvaluationLeaderboardEntry, ...],
    model_cards: tuple[EvaluationModelCard, ...],
    checklist: tuple[EvaluationApprovalChecklistItem, ...],
) -> tuple[str, ...]:
    if not candidates:
        return (
            "No evaluation candidates are available for this project yet.",
            "Create a training run with metrics before comparing models.",
            "Model card evidence will appear after a run is promoted to the registry.",
        )

    leader = leaderboard[0]
    metric_text = (
        f"{leader.primary_metric_name}={leader.primary_metric_value:.4f}"
        if leader.primary_metric_name and leader.primary_metric_value is not None
        else "no primary metric yet"
    )
    passed = sum(1 for item in checklist if item.status == "passed")
    warning = sum(1 for item in checklist if item.status == "warning")
    missing = sum(1 for item in checklist if item.status == "missing")
    return (
        f"{leader.run_name} currently leads the comparison on {metric_text}.",
        f"{len(model_cards)} model card evidence records are linked to registry versions.",
        (
            f"The approval checklist has {passed} passed, {warning} warning, "
            f"and {missing} missing items for reviewer handoff."
        ),
    )


def _candidate_sort_key(
    candidate: EvaluationCandidate,
    primary_metric_name: str | None,
    higher_is_better: bool,
) -> tuple[int, float, int, str]:
    value = _metric_value(candidate, primary_metric_name)
    if value is None:
        return (1, 0.0, -_quality_score(candidate), candidate.run_name)
    ranking_value = -value if higher_is_better else value
    return (0, ranking_value, -_quality_score(candidate), candidate.run_name)


def _baseline_value(
    candidates: tuple[EvaluationCandidate, ...],
    primary_metric_name: str | None,
    higher_is_better: bool,
) -> float | None:
    values = [
        value
        for candidate in candidates
        if (value := _metric_value(candidate, primary_metric_name)) is not None
    ]
    if not values:
        return None
    return min(values) if higher_is_better else max(values)


def _delta_from_baseline(
    value: float | None,
    baseline_value: float | None,
    higher_is_better: bool,
) -> float | None:
    if value is None or baseline_value is None:
        return None
    return value - baseline_value if higher_is_better else baseline_value - value


def _metric_value(
    candidate: EvaluationCandidate,
    metric_name: str | None,
) -> float | None:
    if metric_name is None:
        return None
    return candidate.metrics.get(metric_name)


def _higher_is_better(metric_name: str) -> bool:
    normalized = metric_name.lower()
    return not any(token in normalized for token in _LOWER_IS_BETTER_TOKENS)


def _metric_sort_key(metric_name: str) -> tuple[int, str]:
    try:
        priority = _PRIMARY_METRIC_PRIORITY.index(metric_name)
    except ValueError:
        priority = len(_PRIMARY_METRIC_PRIORITY)
    return (priority, metric_name)


def _quality_score(candidate: EvaluationCandidate) -> int:
    score = 0
    if candidate.status == "succeeded":
        score += 35
    if candidate.metrics:
        score += 25
    if candidate.evaluation_report:
        score += 15
    if candidate.model_version_id is not None:
        score += 10
    if candidate.approval_status == "approved":
        score += 15
    return min(score, 100)


def _model_version_label(candidate: EvaluationCandidate) -> str | None:
    if candidate.registered_model_name is None or candidate.model_version is None:
        return None
    return f"{candidate.registered_model_name} v{candidate.model_version}"


def _evidence_summary(candidate: EvaluationCandidate) -> str:
    label = _model_version_label(candidate)
    if candidate.approval_status == "approved" and label:
        return f"{label} is approved with registry evidence."
    if label:
        return f"{label} is promoted and awaiting final approval."
    if candidate.training_run_id is not None:
        return "Training run metrics are available before registry promotion."
    return "Experiment metrics are available before managed training evidence."


def _lineage_evidence(candidate: EvaluationCandidate) -> str:
    evidence: list[str] = []
    if candidate.dataset_version_id is not None:
        evidence.append(f"dataset_version:{candidate.dataset_version_id}")
    if candidate.feature_set_id is not None:
        evidence.append(f"feature_set:{candidate.feature_set_id}")
    return ", ".join(evidence) if evidence else "missing lineage"


def _model_card_status(
    model_card: EvaluationModelCard | None,
    required_attribute: str,
) -> str:
    if model_card is None:
        return "missing"
    value = getattr(model_card, required_attribute)
    return "passed" if value else "warning"


def _metric_summary(
    metrics: dict[str, float],
    primary_metric_name: str | None,
) -> tuple[EvaluationModelMetric, ...]:
    metric_names = sorted(metrics, key=_metric_sort_key)
    if primary_metric_name and primary_metric_name in metrics:
        metric_names = [primary_metric_name] + [
            metric_name for metric_name in metric_names if metric_name != primary_metric_name
        ]
    return tuple(
        EvaluationModelMetric(
            label=metric_name,
            value=metrics[metric_name],
            tone="success" if metric_name == primary_metric_name else "neutral",
        )
        for metric_name in metric_names[:6]
    )


def _signature_summary(signature: dict[str, object]) -> tuple[str, ...]:
    summary: list[str] = []
    inputs = signature.get("inputs")
    outputs = signature.get("outputs")
    if isinstance(inputs, list):
        summary.append(f"{len(inputs)} inputs")
    if isinstance(outputs, list):
        summary.append(f"{len(outputs)} outputs")
    if not summary and signature:
        summary.append(", ".join(sorted(signature.keys())[:4]))
    return tuple(summary)


def _risk_flags(evidence: EvaluationModelEvidence) -> tuple[str, ...]:
    flags: list[str] = []
    if not evidence.metrics:
        flags.append("missing_metrics")
    if not evidence.signature:
        flags.append("missing_signature")
    if not evidence.artifact_manifest_uri or not evidence.artifact_manifest_hash:
        flags.append("missing_artifact_manifest")
    if evidence.approval_status != "approved":
        flags.append("approval_not_complete")
    if evidence.status == "rejected":
        flags.append("rejected_version")
    return tuple(flags)
