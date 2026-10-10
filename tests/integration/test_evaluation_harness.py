from evaluation.run_evaluation import assess_dataset, calculate_metrics


def test_bootstrap_dataset_cannot_be_reported_as_performance_evidence() -> None:
    document = {
        "metadata": {"synthetic": True, "holdout_tuning_prohibited": True},
        "scenarios": [
            {
                "id": "synthetic",
                "split": "bootstrap",
                "input": {"source": "manual"},
                "support": "Authored contract example",
                "provenance": {"type": "synthetic"},
                "reviewers": [],
            }
        ],
    }

    result = assess_dataset(document)

    assert result["performance_claim_eligible"] is False
    assert "non_synthetic_dataset" in result["unmet_requirements"]
    assert "two_reviewers_for_every_case" in result["unmet_requirements"]


def test_metrics_report_scam_and_availability_outcomes_separately() -> None:
    records = [
        {"expected": "suspected_scam", "actual": "suspected_scam", "status": "complete", "transport_error": None},
        {"expected": "suspected_scam", "actual": "unknown", "status": "unavailable", "transport_error": None},
        {"expected": "legitimate", "actual": "suspected_scam", "status": "partial", "transport_error": None},
        {"expected": "legitimate", "actual": "legitimate", "status": "complete", "transport_error": None},
    ]

    result = calculate_metrics(records)

    assert result["scam_precision"] == 0.5
    assert result["scam_recall"] == 0.5
    assert result["benign_false_positive_rate"] == 0.5
    assert result["partial_count"] == 1
    assert result["unavailable_count"] == 1
