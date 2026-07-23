from collections import Counter
from uuid import UUID, uuid4

from forgeml.modules.drift_detection.domain.entities import (
    DriftAnalysisResult,
    DriftFeatureResult,
    DriftFeatureType,
)


class LocalDriftAnalyzer:
    def analyze(
        self,
        *,
        report_id: UUID,
        baseline_profile: dict[str, object],
        production_samples: list[dict[str, object]],
        default_threshold: float,
    ) -> DriftAnalysisResult:
        feature_results: list[DriftFeatureResult] = []
        for feature_name, raw_config in baseline_profile.items():
            if not isinstance(raw_config, dict):
                continue
            feature_type = str(raw_config.get("type", "")).lower()
            threshold = float(raw_config.get("threshold", default_threshold))
            values = [
                sample[feature_name]
                for sample in production_samples
                if feature_name in sample and sample[feature_name] is not None
            ]
            if not values:
                continue
            if feature_type == DriftFeatureType.NUMERIC.value:
                feature_results.append(
                    _numeric_feature_result(report_id, feature_name, raw_config, values, threshold)
                )
            elif feature_type == DriftFeatureType.CATEGORICAL.value:
                feature_results.append(
                    _categorical_feature_result(
                        report_id,
                        feature_name,
                        raw_config,
                        values,
                        threshold,
                    )
                )
        evaluated_feature_count = len(feature_results)
        drifted_feature_count = sum(1 for result in feature_results if result.drift_detected)
        drift_score = max((result.drift_score for result in feature_results), default=0.0)
        return DriftAnalysisResult(
            drift_score=drift_score,
            drifted_feature_count=drifted_feature_count,
            evaluated_feature_count=evaluated_feature_count,
            summary={
                "max_feature_score": drift_score,
                "drifted_feature_ratio": _safe_rate(drifted_feature_count, evaluated_feature_count),
            },
            feature_results=feature_results,
        )


def _numeric_feature_result(
    report_id: UUID,
    feature_name: str,
    config: dict[str, object],
    values: list[object],
    threshold: float,
) -> DriftFeatureResult:
    numeric_values = [float(value) for value in values if isinstance(value, int | float)]
    if not numeric_values:
        numeric_values = [0.0]
    observed_mean = sum(numeric_values) / len(numeric_values)
    baseline_mean = float(config["mean"])
    baseline_std = float(config["std"])
    scale = max(abs(baseline_mean), baseline_std, 1.0)
    drift_score = min(abs(observed_mean - baseline_mean) / scale, 1.0)
    return DriftFeatureResult(
        id=uuid4(),
        drift_report_id=report_id,
        feature_name=feature_name,
        feature_type=DriftFeatureType.NUMERIC,
        drift_score=drift_score,
        threshold=threshold,
        drift_detected=drift_score > threshold,
        statistics={
            "baseline_mean": baseline_mean,
            "observed_mean": observed_mean,
            "sample_count": len(numeric_values),
        },
    )


def _categorical_feature_result(
    report_id: UUID,
    feature_name: str,
    config: dict[str, object],
    values: list[object],
    threshold: float,
) -> DriftFeatureResult:
    distribution = config["distribution"]
    if not isinstance(distribution, dict):
        distribution = {}
    observed_counts = Counter(str(value) for value in values)
    observed_total = sum(observed_counts.values())
    observed_distribution = {
        category: count / observed_total for category, count in observed_counts.items()
    }
    categories = set(distribution) | set(observed_distribution)
    drift_score = 0.5 * sum(
        abs(float(distribution.get(category, 0.0)) - observed_distribution.get(category, 0.0))
        for category in categories
    )
    return DriftFeatureResult(
        id=uuid4(),
        drift_report_id=report_id,
        feature_name=feature_name,
        feature_type=DriftFeatureType.CATEGORICAL,
        drift_score=drift_score,
        threshold=threshold,
        drift_detected=drift_score > threshold,
        statistics={
            "baseline_distribution": distribution,
            "observed_distribution": observed_distribution,
            "sample_count": observed_total,
        },
    )


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
