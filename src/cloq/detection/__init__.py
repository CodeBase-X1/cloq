"""Detection engine — pipeline of pluggable detectors for sensitive data."""

from cloq.detection.base import BaseDetector, DetectionResult, DetectorRegistry
from cloq.detection.pipeline import DetectionPipeline

__all__ = [
    "BaseDetector",
    "DetectionPipeline",
    "DetectionResult",
    "DetectorRegistry",
]
