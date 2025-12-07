"""Project-specific context loader for domain knowledge injection.

This module provides a system for loading project-specific context from a `.orca/`
directory in the project root. This allows agents to understand domain-specific
patterns, conventions, and architecture before working on a codebase.

Directory Structure:
    .orca/
    ├── project.yaml          # Project metadata and configuration
    ├── architecture.md       # Overall system architecture
    ├── vocabulary.yaml       # Domain-specific terms and meanings
    └── patterns/             # Pattern documentation
        ├── signal_mixin.md   # How to implement SignalMixin
        ├── feature_mixin.md  # How to implement FeatureMixin
        └── ...

Usage:
    from multi_agent_coding_system.config.project_context import ProjectContext

    # Load project context from working directory
    ctx = ProjectContext.load_from_directory("/path/to/trading-repo")

    # Get pattern documentation
    signal_pattern = ctx.get_pattern("signal_mixin")

    # Get full context for injection into agents
    full_context = ctx.get_full_context()
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

ORCA_DIR_NAME = ".orca"
PROJECT_CONFIG_FILE = "project.yaml"
ARCHITECTURE_FILE = "architecture.md"
VOCABULARY_FILE = "vocabulary.yaml"
PATTERNS_DIR = "patterns"


@dataclass
class PatternDoc:
    """Documentation for a specific pattern in the codebase."""
    name: str
    description: str
    content: str
    examples: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)


@dataclass
class VocabularyTerm:
    """A domain-specific term and its meaning."""
    term: str
    definition: str
    examples: List[str] = field(default_factory=list)
    see_also: List[str] = field(default_factory=list)


@dataclass
class ProjectContext:
    """Project-specific context loaded from .orca/ directory."""

    # Project metadata
    project_name: str = ""
    description: str = ""
    tech_stack: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)

    # Architecture documentation
    architecture: str = ""

    # Domain vocabulary
    vocabulary: Dict[str, VocabularyTerm] = field(default_factory=dict)

    # Pattern documentation
    patterns: Dict[str, PatternDoc] = field(default_factory=dict)

    # Custom context sections
    custom_sections: Dict[str, str] = field(default_factory=dict)

    # Source directory
    project_root: str = ""

    @classmethod
    def load_from_directory(cls, project_root: str) -> "ProjectContext":
        """Load project context from the .orca/ directory.

        Args:
            project_root: Path to the project root directory

        Returns:
            ProjectContext instance with loaded data
        """
        ctx = cls(project_root=project_root)
        orca_dir = Path(project_root) / ORCA_DIR_NAME

        if not orca_dir.exists():
            logger.info(f"No .orca/ directory found in {project_root}")
            return ctx

        logger.info(f"Loading project context from {orca_dir}")

        # Load project config
        config_path = orca_dir / PROJECT_CONFIG_FILE
        if config_path.exists():
            ctx._load_project_config(config_path)

        # Load architecture
        arch_path = orca_dir / ARCHITECTURE_FILE
        if arch_path.exists():
            ctx.architecture = arch_path.read_text(encoding="utf-8")

        # Load vocabulary
        vocab_path = orca_dir / VOCABULARY_FILE
        if vocab_path.exists():
            ctx._load_vocabulary(vocab_path)

        # Load patterns
        patterns_dir = orca_dir / PATTERNS_DIR
        if patterns_dir.exists() and patterns_dir.is_dir():
            ctx._load_patterns(patterns_dir)

        # Load any custom markdown files in .orca/
        for md_file in orca_dir.glob("*.md"):
            if md_file.name != ARCHITECTURE_FILE:
                section_name = md_file.stem
                ctx.custom_sections[section_name] = md_file.read_text(encoding="utf-8")

        return ctx

    def _load_project_config(self, config_path: Path) -> None:
        """Load project configuration from YAML."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            self.project_name = config.get("name", "")
            self.description = config.get("description", "")
            self.tech_stack = config.get("tech_stack", [])
            self.entry_points = config.get("entry_points", [])

        except Exception as e:
            logger.warning(f"Failed to load project config: {e}")

    def _load_vocabulary(self, vocab_path: Path) -> None:
        """Load domain vocabulary from YAML."""
        try:
            with open(vocab_path, "r", encoding="utf-8") as f:
                vocab_data = yaml.safe_load(f) or {}

            for term, data in vocab_data.items():
                if isinstance(data, str):
                    # Simple definition
                    self.vocabulary[term] = VocabularyTerm(
                        term=term,
                        definition=data
                    )
                elif isinstance(data, dict):
                    # Full definition with examples
                    self.vocabulary[term] = VocabularyTerm(
                        term=term,
                        definition=data.get("definition", ""),
                        examples=data.get("examples", []),
                        see_also=data.get("see_also", [])
                    )

        except Exception as e:
            logger.warning(f"Failed to load vocabulary: {e}")

    def _load_patterns(self, patterns_dir: Path) -> None:
        """Load pattern documentation from markdown files."""
        for pattern_file in patterns_dir.glob("*.md"):
            try:
                pattern_name = pattern_file.stem
                content = pattern_file.read_text(encoding="utf-8")

                # Parse frontmatter if present
                description = ""
                examples = []
                related_files = []

                if content.startswith("---"):
                    # Has YAML frontmatter
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1]) or {}
                        description = frontmatter.get("description", "")
                        examples = frontmatter.get("examples", [])
                        related_files = frontmatter.get("related_files", [])
                        content = parts[2].strip()

                self.patterns[pattern_name] = PatternDoc(
                    name=pattern_name,
                    description=description,
                    content=content,
                    examples=examples,
                    related_files=related_files
                )

            except Exception as e:
                logger.warning(f"Failed to load pattern {pattern_file}: {e}")

    def get_pattern(self, pattern_name: str) -> Optional[PatternDoc]:
        """Get documentation for a specific pattern.

        Args:
            pattern_name: Name of the pattern (e.g., "signal_mixin")

        Returns:
            PatternDoc if found, None otherwise
        """
        # Try exact match
        if pattern_name in self.patterns:
            return self.patterns[pattern_name]

        # Try normalized name (lowercase, underscores)
        normalized = pattern_name.lower().replace("-", "_").replace(" ", "_")
        if normalized in self.patterns:
            return self.patterns[normalized]

        return None

    def get_vocabulary_term(self, term: str) -> Optional[VocabularyTerm]:
        """Get definition for a domain-specific term."""
        # Try exact match
        if term in self.vocabulary:
            return self.vocabulary[term]

        # Try case-insensitive
        term_lower = term.lower()
        for key, value in self.vocabulary.items():
            if key.lower() == term_lower:
                return value

        return None

    def get_full_context(self) -> str:
        """Get the full project context as a formatted string.

        This is suitable for injection into agent system messages or
        task descriptions.
        """
        sections = []

        # Project info
        if self.project_name:
            sections.append(f"# Project: {self.project_name}\n")
            if self.description:
                sections.append(f"{self.description}\n")

        if self.tech_stack:
            sections.append("## Tech Stack\n")
            sections.append("- " + "\n- ".join(self.tech_stack) + "\n")

        if self.entry_points:
            sections.append("## Entry Points\n")
            sections.append("- " + "\n- ".join(self.entry_points) + "\n")

        # Architecture
        if self.architecture:
            sections.append("## Architecture\n")
            sections.append(self.architecture + "\n")

        # Vocabulary summary
        if self.vocabulary:
            sections.append("## Domain Vocabulary\n")
            for term, vocab in self.vocabulary.items():
                sections.append(f"- **{term}**: {vocab.definition}")
            sections.append("")

        # Pattern summary (just names and descriptions)
        if self.patterns:
            sections.append("## Available Patterns\n")
            for name, pattern in self.patterns.items():
                desc = pattern.description or "(see pattern documentation)"
                sections.append(f"- **{name}**: {desc}")
            sections.append("")

        return "\n".join(sections)

    def get_pattern_context(self, pattern_name: str) -> str:
        """Get formatted context for a specific pattern.

        This includes the full pattern documentation and related vocabulary.
        """
        pattern = self.get_pattern(pattern_name)
        if not pattern:
            return f"Pattern '{pattern_name}' not found in project context."

        sections = [f"# Pattern: {pattern.name}\n"]

        if pattern.description:
            sections.append(f"{pattern.description}\n")

        if pattern.related_files:
            sections.append("## Related Files\n")
            sections.append("- " + "\n- ".join(pattern.related_files) + "\n")

        if pattern.examples:
            sections.append("## Examples\n")
            sections.append("- " + "\n- ".join(pattern.examples) + "\n")

        sections.append("## Implementation Guide\n")
        sections.append(pattern.content)

        return "\n".join(sections)

    def has_context(self) -> bool:
        """Check if any project context was loaded."""
        return bool(
            self.project_name
            or self.architecture
            or self.vocabulary
            or self.patterns
            or self.custom_sections
        )


# Global project context cache
_project_context_cache: Dict[str, ProjectContext] = {}


def get_project_context(project_root: str) -> ProjectContext:
    """Get project context for a directory, with caching.

    Args:
        project_root: Path to the project root directory

    Returns:
        ProjectContext instance
    """
    if project_root not in _project_context_cache:
        _project_context_cache[project_root] = ProjectContext.load_from_directory(
            project_root
        )
    return _project_context_cache[project_root]


def clear_project_context_cache() -> None:
    """Clear the project context cache."""
    _project_context_cache.clear()


def find_pattern_for_task(project_root: str, task_description: str) -> Optional[str]:
    """Attempt to find relevant pattern documentation for a task.

    This does simple keyword matching to find patterns that might be
    relevant to the task description.

    Args:
        project_root: Path to the project root directory
        task_description: The task description to match against

    Returns:
        Pattern context string if found, None otherwise
    """
    ctx = get_project_context(project_root)
    if not ctx.patterns:
        return None

    task_lower = task_description.lower()

    # Look for pattern names in the task description
    for pattern_name, pattern in ctx.patterns.items():
        # Check if pattern name appears in task
        name_variants = [
            pattern_name,
            pattern_name.replace("_", " "),
            pattern_name.replace("_", ""),
        ]
        for variant in name_variants:
            if variant.lower() in task_lower:
                return ctx.get_pattern_context(pattern_name)

    return None
