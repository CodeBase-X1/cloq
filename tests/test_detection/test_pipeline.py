"""Tests for the detection pipeline."""

from __future__ import annotations

from cloq.detection.base import DetectionResult
from cloq.detection.pipeline import DetectionPipeline


class TestPipelineExecution:
    def test_runs_all_detectors(self, pipeline: DetectionPipeline) -> None:
        text = "Key: AKIAIOSFODNN7EXAMPLE, email: test@example.com, server: 10.0.1.50"
        results, metrics = pipeline.run(text)
        assert len(results) >= 3
        assert metrics.total_detections == len(results)

    def test_returns_metrics(self, pipeline: DetectionPipeline) -> None:
        text = "Just some normal text"
        _results, metrics = pipeline.run(text)
        assert metrics.total_duration_ms >= 0
        assert "secrets" in metrics.detector_durations
        assert "pii" in metrics.detector_durations
        assert "network" in metrics.detector_durations

    def test_empty_text(self, pipeline: DetectionPipeline) -> None:
        results, metrics = pipeline.run("")
        assert len(results) == 0
        assert metrics.total_detections == 0


class TestOverlapMerging:
    def test_merges_overlapping_results(self) -> None:
        results = [
            DetectionResult(
                entity_type="TYPE_A",
                start=0,
                end=10,
                score=0.8,
                original_text="0123456789",
                detector_name="a",
            ),
            DetectionResult(
                entity_type="TYPE_B",
                start=5,
                end=15,
                score=0.9,
                original_text="567890abcde",
                detector_name="b",
            ),
        ]
        merged = DetectionPipeline._merge_overlapping(results)
        # Higher score should win
        assert len(merged) == 1
        assert merged[0].entity_type == "TYPE_B"

    def test_keeps_non_overlapping(self) -> None:
        results = [
            DetectionResult(
                entity_type="TYPE_A",
                start=0,
                end=5,
                score=0.9,
                original_text="01234",
                detector_name="a",
            ),
            DetectionResult(
                entity_type="TYPE_B",
                start=10,
                end=15,
                score=0.9,
                original_text="abcde",
                detector_name="b",
            ),
        ]
        merged = DetectionPipeline._merge_overlapping(results)
        assert len(merged) == 2

    def test_empty_results(self) -> None:
        merged = DetectionPipeline._merge_overlapping([])
        assert merged == []
