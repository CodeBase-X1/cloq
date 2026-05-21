"""Detection pipeline — orchestrates multiple detectors and merges results."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloq.detection.base import BaseDetector, DetectionResult


@dataclass
class PipelineMetrics:
    """Performance metrics for a pipeline run."""

    total_detections: int = 0
    total_duration_ms: float = 0.0
    detector_durations: dict[str, float] = field(default_factory=dict)


class DetectionPipeline:
    """Orchestrates multiple detectors and merges their results.

    The pipeline runs each detector in sequence, collects all results,
    and merges overlapping detections (keeping the highest-confidence one).

    Args:
        detectors: Ordered list of detectors to run.

    Example::

        pipeline = DetectionPipeline([
            SecretsDetector(),
            PIIDetector(),
            NetworkDetector(),
        ])
        results, metrics = pipeline.run("My key is AKIAIOSFODNN7EXAMPLE")
    """

    def __init__(self, detectors: list[BaseDetector]) -> None:
        self._detectors = detectors

    @property
    def detectors(self) -> list[BaseDetector]:
        """Return the list of active detectors."""
        return list(self._detectors)

    def run(self, text: str) -> tuple[list[DetectionResult], PipelineMetrics]:
        """Run all detectors on *text* and return merged results with metrics.

        Args:
            text: The input string to scan.

        Returns:
            A tuple of ``(merged_results, metrics)``.
        """
        all_results: list[DetectionResult] = []
        metrics = PipelineMetrics()

        for detector in self._detectors:
            t0 = time.perf_counter()
            results = detector.detect(text)
            duration_ms = (time.perf_counter() - t0) * 1000

            all_results.extend(results)
            metrics.detector_durations[detector.name] = round(duration_ms, 3)

        # Merge overlapping detections
        merged = self._merge_overlapping(all_results)

        metrics.total_detections = len(merged)
        metrics.total_duration_ms = round(sum(metrics.detector_durations.values()), 3)

        return merged, metrics

    @staticmethod
    def _merge_overlapping(results: list[DetectionResult]) -> list[DetectionResult]:
        """Merge overlapping detections, keeping the highest-confidence result.

        When two detections overlap, the one with the higher score is kept.
        If scores are equal, the longer span wins.
        """
        if not results:
            return []

        # Sort by start position, then by score descending
        sorted_results = sorted(results, key=lambda r: (r.start, -r.score))
        merged: list[DetectionResult] = [sorted_results[0]]

        for current in sorted_results[1:]:
            previous = merged[-1]

            if current.overlaps(previous):
                # Keep the one with higher confidence; on tie, keep longer span
                if current.score > previous.score or (
                    current.score == previous.score and current.length > previous.length
                ):
                    merged[-1] = current
                # else: keep previous (already in merged)
            else:
                merged.append(current)

        return merged
