"""Output validator for the AI Agent Framework.

Validates AI-generated output with support for:
- JSON validation (parse and structure)
- Schema validation (Pydantic model or dict schema)
- Required fields checking
- Business rule validation (custom validators)
- Automatic repair of invalid output (retry with repair prompt)
- Configurable retry on validation failure

The ``OutputValidator`` is used by ``BaseAgent`` after AI execution
to ensure the response meets the expected format and quality.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from src.ai.agents.exceptions import OutputValidationError, OutputRepairError
from src.core.logging import get_logger


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------
class ValidationResult(BaseModel):
    """Result of output validation.

    Attributes:
        is_valid: Whether the output passed validation.
        errors: List of validation error messages.
        warnings: List of non-fatal warnings.
        repaired: Whether the output was repaired.
        repaired_output: The repaired output, if repair was performed.
        structured_data: Parsed structured data, if applicable.
    """

    is_valid: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    repaired: bool = False
    repaired_output: str | None = None
    structured_data: dict[str, Any] | None = None

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def valid(cls, *, structured_data: dict[str, Any] | None = None) -> ValidationResult:
        """Create a valid result."""
        return cls(is_valid=True, structured_data=structured_data)

    @classmethod
    def invalid(cls, errors: list[str], *, warnings: list[str] | None = None) -> ValidationResult:
        """Create an invalid result."""
        return cls(is_valid=False, errors=errors, warnings=warnings or [])


# ---------------------------------------------------------------------------
# Business rule validator
# ---------------------------------------------------------------------------
class BusinessRule:
    """A business rule validator for output checking.

    Attributes:
        name: The rule name for logging.
        validator: A callable that takes the parsed output and returns
            ``(is_valid, error_message)``.
    """

    def __init__(
        self,
        name: str,
        validator: Any,
    ) -> None:
        self.name = name
        self.validator = validator

    def check(self, data: Any) -> tuple[bool, str | None]:
        """Check the rule against the data.

        Args:
            data: The parsed output data.

        Returns:
            A tuple of (is_valid, error_message).
        """
        try:
            return self.validator(data)
        except Exception as exc:
            return False, f"Rule '{self.name}' raised exception: {exc}"


# ---------------------------------------------------------------------------
# Output validator
# ---------------------------------------------------------------------------
class OutputValidator:
    """Validates AI-generated output.

    Supports multiple validation strategies:
    - JSON parsing validation
    - Pydantic schema validation
    - Required field checking
    - Custom business rules

    Attributes:
        schema: Optional Pydantic model class for schema validation.
        required_fields: List of required field names in JSON output.
        business_rules: List of business rule validators.
        max_repair_attempts: Maximum repair attempts before failing.
    """

    def __init__(
        self,
        *,
        schema: type[BaseModel] | None = None,
        required_fields: list[str] | None = None,
        business_rules: list[BusinessRule] | None = None,
        max_repair_attempts: int = 2,
    ) -> None:
        """Initialize the output validator.

        Args:
            schema: Optional Pydantic model class for schema validation.
            required_fields: List of required field names in JSON output.
            business_rules: List of business rule validators.
            max_repair_attempts: Maximum repair attempts.
        """
        self._schema = schema
        self._required_fields = required_fields or []
        self._business_rules = business_rules or []
        self._max_repair_attempts = max_repair_attempts
        self._logger = get_logger(__name__)

    @property
    def has_schema(self) -> bool:
        """Check if a schema is configured."""
        return self._schema is not None

    def add_business_rule(self, rule: BusinessRule) -> None:
        """Add a business rule validator.

        Args:
            rule: The business rule to add.
        """
        self._business_rules.append(rule)

    def validate(self, output: str) -> ValidationResult:
        """Validate AI output.

        Args:
            output: The raw AI output string.

        Returns:
            A ``ValidationResult`` indicating success or failure.
        """
        errors: list[str] = []
        warnings: list[str] = []
        structured_data: dict[str, Any] | None = None

        # Step 1: Try JSON parsing if schema or required fields are configured
        if self._schema is not None or self._required_fields:
            cleaned = _clean_json_output(output)
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    structured_data = parsed
                else:
                    errors.append(f"Expected JSON object, got {type(parsed).__name__}")
            except json.JSONDecodeError as exc:
                errors.append(f"JSON parsing failed: {exc}")

            # Step 2: Check required fields
            if structured_data is not None and not errors:
                for field in self._required_fields:
                    if field not in structured_data:
                        errors.append(f"Required field '{field}' is missing")

            # Step 3: Schema validation
            if structured_data is not None and not errors and self._schema is not None:
                try:
                    self._schema.model_validate(structured_data)
                except PydanticValidationError as exc:
                    for err in exc.errors():
                        loc = ".".join(str(l) for l in err["loc"])
                        errors.append(f"Schema validation: {loc} - {err['msg']}")

            # Step 4: Business rules
            if structured_data is not None and not errors:
                for rule in self._business_rules:
                    is_valid, error_msg = rule.check(structured_data)
                    if not is_valid:
                        errors.append(f"Business rule '{rule.name}': {error_msg}")

        else:
            # No schema or required fields — just check non-empty
            if not output or not output.strip():
                errors.append("Output is empty")

        if errors:
            return ValidationResult.invalid(errors, warnings=warnings)
        return ValidationResult.valid(structured_data=structured_data)

    def validate_and_repair(
        self,
        output: str,
        *,
        repair_fn: Any | None = None,
    ) -> ValidationResult:
        """Validate output and attempt repair if invalid.

        Args:
            output: The raw AI output string.
            repair_fn: Optional async callable that takes the invalid
                output and error messages, and returns a repaired string.
                If None, no repair is attempted.

        Returns:
            A ``ValidationResult`` — if repair succeeded, ``repaired``
            will be True and ``repaired_output`` will contain the
            repaired string.
        """
        result = self.validate(output)

        if result.is_valid:
            return result

        if repair_fn is None:
            return result

        self._logger.info(
            "output_repair_attempting",
            errors=result.errors,
            max_attempts=self._max_repair_attempts,
        )

        current_output = output
        for attempt in range(self._max_repair_attempts):
            try:
                repaired = repair_fn(current_output, result.errors)
            except Exception as exc:
                self._logger.warning(
                    "output_repair_failed",
                    attempt=attempt + 1,
                    error=str(exc),
                )
                continue

            if repaired is None:
                break

            repair_result = self.validate(repaired)
            if repair_result.is_valid:
                self._logger.info(
                    "output_repair_succeeded",
                    attempt=attempt + 1,
                )
                return ValidationResult(
                    is_valid=True,
                    warnings=result.errors,  # Original errors as warnings
                    repaired=True,
                    repaired_output=repaired,
                    structured_data=repair_result.structured_data,
                )

            current_output = repaired
            result = repair_result

        self._logger.warning(
            "output_repair_exhausted",
            attempts=self._max_repair_attempts,
        )
        return ValidationResult(
            is_valid=False,
            errors=result.errors,
            warnings=[f"Repair failed after {self._max_repair_attempts} attempts"],
        )


# ---------------------------------------------------------------------------
# JSON cleaning helpers
# ---------------------------------------------------------------------------
def _clean_json_output(raw: str) -> str:
    """Clean LLM output before JSON parsing.

    Handles common formatting issues:
    - Markdown code fences (```json ... ``` or ``` ... ```)
    - Leading/trailing prose around the JSON object
    - Trailing commas before closing brackets
    - Unquoted property names (e.g. ``{key: value}``)
    - Single-quoted strings (e.g. ``{'key': 'value'}``)
    - JavaScript-style comments (``//`` and ``/* */``)

    Args:
        raw: The raw LLM output string.

    Returns:
        A cleaned string that is more likely to parse as valid JSON.
    """
    text = raw.strip()

    # Remove markdown code fences
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)

    # If there's still non-JSON text around a JSON object, try to extract
    # the outermost { ... } block.
    if text and not text.startswith("{") and not text.startswith("["):
        brace_start = text.find("{")
        bracket_start = text.find("[")
        if brace_start != -1 and (bracket_start == -1 or brace_start < bracket_start):
            brace_end = text.rfind("}")
            if brace_end != -1 and brace_end > brace_start:
                text = text[brace_start : brace_end + 1]
        elif bracket_start != -1:
            bracket_end = text.rfind("]")
            if bracket_end != -1 and bracket_end > bracket_start:
                text = text[bracket_start : bracket_end + 1]

    # Remove trailing commas before closing brackets (common LLM error)
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # If the basic cleaning produced valid JSON, return immediately.
    try:
        json.loads(text)
        return text.strip()
    except json.JSONDecodeError:
        pass

    # Apply more aggressive repairs for common LLM JSON issues.
    text = _repair_json_text(text)

    return text.strip()


def _repair_json_text(text: str) -> str:
    """Aggressively repair common LLM JSON issues using a state machine.

    Handles:
    - Unquoted property names → double-quoted
    - Single-quoted strings → double-quoted (escaping inner double quotes)
    - JavaScript-style comments (``//`` line and ``/* */`` block) → removed
    - Trailing commas before closing brackets → removed

    This is a fallback after basic cleaning fails to produce valid JSON.
    """
    result: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    string_quote: str | None = None

    while i < n:
        ch = text[i]

        if in_string:
            # Escape sequence — keep as-is (handle single-quote escapes)
            if ch == "\\" and i + 1 < n:
                next_ch = text[i + 1]
                if string_quote == "'" and next_ch == "'":
                    # \' inside single-quoted string → just '
                    result.append("'")
                    i += 2
                    continue
                result.append(ch)
                result.append(next_ch)
                i += 2
                continue
            if ch == string_quote:
                # End of string — always emit a double quote
                result.append('"')
                in_string = False
                string_quote = None
                i += 1
                continue
            # Inside a single-quoted string, escape any literal double quotes
            if string_quote == "'" and ch == '"':
                result.append('\\"')
                i += 1
                continue
            result.append(ch)
            i += 1
            continue

        # --- Not in string ---

        # String start (single or double quote)
        if ch == '"' or ch == "'":
            in_string = True
            string_quote = ch
            result.append('"')  # always open with double quote
            i += 1
            continue

        # JavaScript comments
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            i += 2
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue

        # Unquoted property names: after { or , (with optional whitespace)
        if ch in "{,":
            result.append(ch)
            i += 1
            # Skip whitespace
            while i < n and text[i] in " \t\n\r":
                result.append(text[i])
                i += 1
            # Check for unquoted identifier
            if i < n and (text[i].isalpha() or text[i] == "_"):
                ident_start = i
                while i < n and (text[i].isalnum() or text[i] in "_-"):
                    i += 1
                ident = text[ident_start:i]
                # Skip whitespace before colon
                while i < n and text[i] in " \t\n\r":
                    i += 1
                if i < n and text[i] == ":":
                    result.append(f'"{ident}"')
                else:
                    result.append(ident)
            continue

        result.append(ch)
        i += 1

    text = "".join(result)
    # Remove trailing commas before closing brackets (may be introduced by
    # comment removal or were already present)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text
