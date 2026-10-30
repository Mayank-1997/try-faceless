"""Quality evaluator for the AI Agent Framework.

Provides reusable quality scoring for AI-generated output:

- **Completeness**: Does the output cover all required aspects?
- **Length**: Is the output within expected length bounds?
- **Consistency**: Is the output internally consistent?
- **Readability**: Is the output well-structured and readable?
- **Score calculation**: Weighted aggregate score (0.0–1.0)
- **Pass/Fail**: Configurable threshold for quality gate
- **Future LLM-as-a-Judge**: Interface for LLM-based quality evaluation

The ``QualityEvaluator`` is used by ``BaseAgent`` after output
validation to score the quality of the generated content.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.logging import get_logger


# ---------------------------------------------------------------------------
# Quality dimension scores
# ---------------------------------------------------------------------------
class QualityDimensions(BaseModel):
    """Scores for individual quality dimensions.

    Each dimension is scored from 0.0 to 1.0.

    Attributes:
        completeness: How completely the output covers the topic.
        length: How well the output length matches expectations.
        consistency: How internally consistent the output is.
        readability: How readable and well-structured the output is.
        relevance: How relevant the output is to the prompt.
        accuracy: How accurate the output appears to be.
    """

    completeness: float = 0.0
    length: float = 0.0
    consistency: float = 0.0
    readability: float = 0.0
    relevance: float = 0.0
    accuracy: float = 0.0

    def as_dict(self) -> dict[str, float]:
        """Return dimensions as a dictionary."""
        return {
            "completeness": self.completeness,
            "length": self.length,
            "consistency": self.consistency,
            "readability": self.readability,
            "relevance": self.relevance,
            "accuracy": self.accuracy,
        }


# ---------------------------------------------------------------------------
# Quality evaluation result
# ---------------------------------------------------------------------------
class QualityResult(BaseModel):
    """Result of quality evaluation.

    Attributes:
        score: Aggregate quality score (0.0–1.0).
        dimensions: Individual dimension scores.
        passed: Whether the score meets the threshold.
        threshold: The pass/fail threshold.
        notes: Evaluation notes and observations.
        suggestions: Improvement suggestions.
    """

    score: float = 0.0
    dimensions: QualityDimensions = Field(default_factory=QualityDimensions)
    passed: bool = False
    threshold: float = 0.7
    notes: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

    @property
    def score_percentage(self) -> float:
        """Score as a percentage (0–100)."""
        return self.score * 100.0

    @property
    def grade(self) -> str:
        """Letter grade based on score."""
        if self.score >= 0.9:
            return "A"
        if self.score >= 0.8:
            return "B"
        if self.score >= 0.7:
            return "C"
        if self.score >= 0.6:
            return "D"
        return "F"


# ---------------------------------------------------------------------------
# Quality dimension evaluator (callable)
# ---------------------------------------------------------------------------
class DimensionEvaluator:
    """Evaluates a single quality dimension.

    Attributes:
        name: The dimension name.
        weight: The weight of this dimension in the aggregate score.
        evaluator: A callable that takes the output and returns a 0.0–1.0 score.
    """

    def __init__(
        self,
        name: str,
        weight: float,
        evaluator: Any,
    ) -> None:
        self.name = name
        self.weight = weight
        self.evaluator = evaluator

    def evaluate(self, output: str, context: dict[str, Any] | None = None) -> float:
        """Evaluate the dimension.

        Args:
            output: The AI output to evaluate.
            context: Optional context (prompt, variables, etc.).

        Returns:
            A score from 0.0 to 1.0.
        """
        try:
            score = self.evaluator(output, context or {})
            return max(0.0, min(1.0, float(score)))
        except Exception:
            return 0.0


# ---------------------------------------------------------------------------
# Built-in dimension evaluators
# ---------------------------------------------------------------------------
def _eval_completeness(output: str, context: dict[str, Any]) -> float:
    """Evaluate completeness based on output length and required keywords."""
    if not output:
        return 0.0
    min_length = context.get("min_length", 50)
    required_keywords = context.get("required_keywords", [])
    length_score = min(1.0, len(output) / min_length) if min_length > 0 else 1.0
    keyword_score = 1.0
    if required_keywords:
        found = sum(1 for kw in required_keywords if kw.lower() in output.lower())
        keyword_score = found / len(required_keywords)
    return (length_score + keyword_score) / 2


def _eval_length(output: str, context: dict[str, Any]) -> float:
    """Evaluate length against expected bounds."""
    if not output:
        return 0.0
    min_len = context.get("min_length", 10)
    max_len = context.get("max_length", 10000)
    length = len(output)
    if length < min_len:
        return length / min_len if min_len > 0 else 0.0
    if length > max_len:
        return max_len / length if length > 0 else 0.0
    return 1.0


def _eval_consistency(output: str, context: dict[str, Any]) -> float:
    """Evaluate internal consistency (basic heuristic)."""
    if not output:
        return 0.0
    # Check for contradictions (very basic — looks for negation patterns)
    sentences = output.split(". ")
    if len(sentences) <= 1:
        return 1.0
    # Simple heuristic: check for repeated content
    unique = len(set(s.strip().lower() for s in sentences if s.strip()))
    return min(1.0, unique / len(sentences))


def _eval_readability(output: str, context: dict[str, Any]) -> float:
    """Evaluate readability (basic heuristic based on structure)."""
    if not output:
        return 0.0
    score = 0.0
    # Has paragraphs
    if "\n\n" in output:
        score += 0.3
    # Has headings or structure
    if any(marker in output for marker in ["#", "##", "- ", "* ", "1. "]):
        score += 0.3
    # Reasonable sentence length
    sentences = [s for s in output.split(".") if s.strip()]
    if sentences:
        avg_len = sum(len(s) for s in sentences) / len(sentences)
        if 10 <= avg_len <= 200:
            score += 0.4
    return min(1.0, score)


def _eval_relevance(output: str, context: dict[str, Any]) -> float:
    """Evaluate relevance to the prompt (basic keyword overlap)."""
    if not output:
        return 0.0
    prompt = context.get("prompt", "")
    if not prompt:
        return 0.8  # Default if no prompt provided
    prompt_words = set(prompt.lower().split())
    output_words = set(output.lower().split())
    if not prompt_words:
        return 0.8
    overlap = len(prompt_words & output_words) / len(prompt_words)
    return min(1.0, overlap * 1.5)  # Slight boost since not all prompt words need to appear


def _eval_accuracy(output: str, context: dict[str, Any]) -> float:
    """Evaluate accuracy (placeholder — future LLM-as-a-Judge)."""
    if not output:
        return 0.0
    return 0.8  # Default neutral score; will be replaced by LLM evaluation


# ---------------------------------------------------------------------------
# Quality evaluator
# ---------------------------------------------------------------------------
class QualityEvaluator:
    """Evaluates the quality of AI-generated output.

    Combines multiple dimension evaluators with configurable weights
    to produce an aggregate quality score.

    Attributes:
        threshold: The minimum score required to pass.
        dimensions: List of dimension evaluators with weights.
    """

    def __init__(
        self,
        *,
        threshold: float = 0.7,
        dimensions: list[DimensionEvaluator] | None = None,
    ) -> None:
        """Initialize the quality evaluator.

        Args:
            threshold: Minimum score to pass (0.0–1.0).
            dimensions: Custom dimension evaluators. If None, uses defaults.
        """
        self.threshold = threshold
        self._logger = get_logger(__name__)

        if dimensions is not None:
            self._dimensions = dimensions
        else:
            # Default dimensions with equal weights
            self._dimensions = [
                DimensionEvaluator("completeness", 0.2, _eval_completeness),
                DimensionEvaluator("length", 0.15, _eval_length),
                DimensionEvaluator("consistency", 0.15, _eval_consistency),
                DimensionEvaluator("readability", 0.2, _eval_readability),
                DimensionEvaluator("relevance", 0.2, _eval_relevance),
                DimensionEvaluator("accuracy", 0.1, _eval_accuracy),
            ]

    @property
    def dimension_names(self) -> list[str]:
        """Return the names of all evaluated dimensions."""
        return [d.name for d in self._dimensions]

    def evaluate(
        self,
        output: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> QualityResult:
        """Evaluate the quality of AI output.

        Args:
            output: The AI-generated output to evaluate.
            context: Optional context (prompt, required keywords, etc.).

        Returns:
            A ``QualityResult`` with scores and pass/fail status.
        """
        ctx = context or {}
        dimension_scores = QualityDimensions()
        notes: list[str] = []
        suggestions: list[str] = []

        total_weight = sum(d.weight for d in self._dimensions)
        if total_weight == 0:
            total_weight = 1.0

        weighted_sum = 0.0

        for dim in self._dimensions:
            score = dim.evaluate(output, ctx)
            weighted_sum += score * dim.weight

            # Set the corresponding dimension score
            if hasattr(dimension_scores, dim.name):
                setattr(dimension_scores, dim.name, round(score, 4))

            if score < 0.5:
                notes.append(f"Low {dim.name} score: {score:.2f}")
                suggestions.append(f"Improve {dim.name}")

        aggregate = weighted_sum / total_weight
        aggregate = round(aggregate, 4)

        passed = aggregate >= self.threshold

        if not passed:
            notes.append(f"Score {aggregate:.2f} below threshold {self.threshold:.2f}")

        result = QualityResult(
            score=aggregate,
            dimensions=dimension_scores,
            passed=passed,
            threshold=self.threshold,
            notes=notes,
            suggestions=suggestions,
        )

        self._logger.info(
            "quality_evaluated",
            score=aggregate,
            passed=passed,
            threshold=self.threshold,
            grade=result.grade,
        )

        return result

    def add_dimension(self, dimension: DimensionEvaluator) -> None:
        """Add a custom dimension evaluator.

        Args:
            dimension: The dimension evaluator to add.
        """
        self._dimensions.append(dimension)
