from uuid import uuid4

from forgeml.modules.drift_detection.infrastructure.analyzer import LocalDriftAnalyzer


def test_local_drift_analyzer_scores_numeric_and_categorical_shift() -> None:
    analyzer = LocalDriftAnalyzer()

    result = analyzer.analyze(
        report_id=uuid4(),
        baseline_profile={
            "amount": {"type": "numeric", "mean": 100.0, "std": 20.0, "threshold": 0.2},
            "merchant_category": {
                "type": "categorical",
                "distribution": {"grocery": 0.8, "travel": 0.2},
                "threshold": 0.25,
            },
        },
        production_samples=[
            {"amount": 160.0, "merchant_category": "travel"},
            {"amount": 180.0, "merchant_category": "travel"},
            {"amount": 140.0, "merchant_category": "travel"},
        ],
        default_threshold=0.2,
    )

    assert result.evaluated_feature_count == 2
    assert result.drifted_feature_count == 2
    assert result.drift_score > 0.5
    assert {feature.feature_name for feature in result.feature_results} == {
        "amount",
        "merchant_category",
    }
