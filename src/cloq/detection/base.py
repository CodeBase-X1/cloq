"""Base classes and data structures for the detection engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """A single detected sensitive entity within text.

    Attributes:
        entity_type: Category of the detection (e.g., ``AWS_KEY``, ``EMAIL``).
        start: Start character index in the source text (inclusive).
        end: End character index in the source text (exclusive).
        score: Confidence score in ``[0.0, 1.0]``.
        original_text: The exact substring that was matched.
        detector_name: Name of the detector that produced this result.
    """

    entity_type: str
    start: int
    end: int
    score: float
    original_text: str
    detector_name: str

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"start must be >= 0, got {self.start}")
        if self.end <= self.start:
            raise ValueError(f"end ({self.end}) must be > start ({self.start})")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0.0, 1.0], got {self.score}")

    @property
    def length(self) -> int:
        """Length of the matched text span."""
        return self.end - self.start

    def overlaps(self, other: DetectionResult) -> bool:
        """Return ``True`` if this result's span overlaps with *other*."""
        return self.start < other.end and other.start < self.end


class BaseDetector(ABC):
    """Abstract base class for all sensitive-data detectors.

    Subclasses must implement :meth:`detect` and set :attr:`name`.
    """

    name: ClassVar[str]
    """Unique identifier for this detector."""

    @abstractmethod
    def detect(self, text: str) -> list[DetectionResult]:
        """Scan *text* and return all detected sensitive entities.

        Args:
            text: The input string to analyse.

        Returns:
            A list of :class:`DetectionResult` instances, possibly empty.
        """

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r}>"


class DetectorRegistry:
    """Plugin registry for auto-discovery of detector classes.

    Example::

        registry = DetectorRegistry()
        registry.register(SecretsDetector)
        registry.register(PIIDetector)

        for detector in registry.get_all():
            results = detector.detect(text)
    """

    def __init__(self) -> None:
        self._detectors: dict[str, BaseDetector] = {}

    def register(self, detector: BaseDetector) -> None:
        """Register a detector instance.

        Args:
            detector: An instance of a :class:`BaseDetector` subclass.

        Raises:
            ValueError: If a detector with the same name is already registered.
        """
        if detector.name in self._detectors:
            raise ValueError(
                f"Detector {detector.name!r} is already registered. "
                "Use a unique name for each detector."
            )
        self._detectors[detector.name] = detector

    def get(self, name: str) -> BaseDetector | None:
        """Look up a detector by name, returning ``None`` if not found."""
        return self._detectors.get(name)

    def get_all(self) -> list[BaseDetector]:
        """Return all registered detectors in registration order."""
        return list(self._detectors.values())

    def unregister(self, name: str) -> None:
        """Remove a detector by name.

        Raises:
            KeyError: If no detector with *name* exists.
        """
        if name not in self._detectors:
            raise KeyError(f"No detector registered with name {name!r}")
        del self._detectors[name]

    @property
    def names(self) -> list[str]:
        """Return names of all registered detectors."""
        return list(self._detectors.keys())

    def __len__(self) -> int:
        return len(self._detectors)

    def __contains__(self, name: str) -> bool:
        return name in self._detectors
