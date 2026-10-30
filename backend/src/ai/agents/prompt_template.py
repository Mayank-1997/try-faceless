"""Prompt template abstraction for the AI Agent Framework.

Provides a strongly-typed prompt template model with:
- Versioning (semantic version string)
- Variable definitions with default values
- Metadata (author, description, tags, model compatibility)
- Validation of required variables before rendering
- Rendering with variable substitution

This abstraction wraps the existing ``PromptManager`` and provides
a programmatic interface for defining prompts in code, complementing
the file-based prompt loading system.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from src.ai.agents.exceptions import PromptRenderingError, PromptValidationError


# Regex to find {{variable}} placeholders
_VARIABLE_RE = re.compile(r"\{\{(\w+)\}\}")


class PromptVariable(BaseModel):
    """Definition of a prompt template variable.

    Attributes:
        name: The variable name (must match ``{{name}}`` in template).
        description: Human-readable description of the variable.
        default_value: Optional default value if not provided.
        required: Whether this variable must be provided.
    """

    name: str
    description: str = ""
    default_value: Any = None
    required: bool = True


class PromptTemplateMetadata(BaseModel):
    """Metadata for a prompt template.

    Attributes:
        version: Semantic version string (e.g. "1.0.0").
        author: Author name.
        description: Human-readable description.
        tags: Categorization tags.
        model_compatibility: List of model names this prompt is designed for.
        temperature: Recommended sampling temperature.
        max_output_tokens: Recommended max output tokens.
    """

    version: str = "1.0.0"
    author: str = "system"
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    model_compatibility: list[str] = Field(default_factory=list)
    temperature: float = 0.7
    max_output_tokens: int = 8192


class PromptTemplate(BaseModel):
    """A prompt template with variables, metadata, and rendering.

    Attributes:
        name: The template name (e.g. "web_search", "script_generation").
        template: The raw template string with ``{{variable}}`` placeholders.
        variables: List of variable definitions.
        metadata: Template metadata (version, author, etc.).
    """

    name: str
    template: str
    variables: list[PromptVariable] = Field(default_factory=list)
    metadata: PromptTemplateMetadata = Field(default_factory=PromptTemplateMetadata)

    model_config = {"arbitrary_types_allowed": True}

    @property
    def version(self) -> str:
        """Return the template version."""
        return self.metadata.version

    @property
    def required_variables(self) -> list[str]:
        """Return the names of required variables."""
        return [v.name for v in self.variables if v.required]

    @property
    def optional_variables(self) -> list[str]:
        """Return the names of optional variables."""
        return [v.name for v in self.variables if not v.required]

    @property
    def all_variable_names(self) -> list[str]:
        """Return all variable names."""
        return [v.name for v in self.variables]

    @property
    def template_variables(self) -> set[str]:
        """Return the set of variables found in the template string."""
        return set(_VARIABLE_RE.findall(self.template))

    def validate_variables(self, provided: dict[str, Any]) -> None:
        """Validate that all required variables are provided.

        Args:
            provided: Dictionary of provided variable values.

        Raises:
            PromptValidationError: If required variables are missing.
        """
        provided_keys = set(provided.keys())
        required_keys = set(self.required_variables)
        missing = required_keys - provided_keys

        # Check for variables in template that aren't defined
        template_vars = self.template_variables
        undefined_in_model = template_vars - set(self.all_variable_names)
        if undefined_in_model:
            # These are implicitly required if they have no default
            missing |= (undefined_in_model - provided_keys)

        if missing:
            raise PromptValidationError(self.name, sorted(missing))

    def render(self, variables: dict[str, Any]) -> str:
        """Render the prompt template with variable substitution.

        Args:
            variables: Dictionary of variable names to values.

        Returns:
            The rendered prompt string.

        Raises:
            PromptValidationError: If required variables are missing.
            PromptRenderingError: If rendering fails.
        """
        # Merge with defaults
        merged: dict[str, Any] = {}
        for var in self.variables:
            if not var.required and var.default_value is not None:
                merged[var.name] = var.default_value
        merged.update(variables)

        # Validate
        self.validate_variables(merged)

        # Substitute
        try:
            rendered = self.template
            for key, value in merged.items():
                rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
            return rendered
        except Exception as exc:
            raise PromptRenderingError(self.name, str(exc)) from exc

    @classmethod
    def from_string(
        cls,
        name: str,
        template: str,
        *,
        version: str = "1.0.0",
        description: str = "",
    ) -> PromptTemplate:
        """Create a ``PromptTemplate`` from a raw template string.

        Automatically extracts variable names from the template.

        Args:
            name: The template name.
            template: The raw template string with ``{{variable}}`` placeholders.
            version: Semantic version.
            description: Human-readable description.

        Returns:
            A ``PromptTemplate`` with auto-detected variables.
        """
        var_names = sorted(set(_VARIABLE_RE.findall(template)))
        variables = [PromptVariable(name=v) for v in var_names]
        return cls(
            name=name,
            template=template,
            variables=variables,
            metadata=PromptTemplateMetadata(
                version=version,
                description=description,
            ),
        )
