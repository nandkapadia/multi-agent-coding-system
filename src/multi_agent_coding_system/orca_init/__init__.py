"""Orca Init - Interactive agent for generating .orca/ project context.

This tool analyzes a codebase and generates the .orca/ directory with:
- project.yaml: Project metadata and configuration
- architecture.md: System architecture documentation
- vocabulary.yaml: Domain-specific terms and definitions
- patterns/: Implementation pattern documentation

Usage:
    python -m multi_agent_coding_system.orca_init /path/to/project

    # Or with the CLI
    orca-init /path/to/project

    # Non-interactive mode
    orca-init --non-interactive /path/to/project

    # Dry run (show what would be generated)
    orca-init --dry-run /path/to/project
"""

from multi_agent_coding_system.orca_init.analyzer import (
    analyze_codebase,
    CodebaseAnalysis,
    FileStats,
)
from multi_agent_coding_system.orca_init.detector import (
    detect_patterns,
    PatternDetectionResult,
    DetectedPattern,
    VocabularyTerm,
)
from multi_agent_coding_system.orca_init.generator import generate_orca_config
from multi_agent_coding_system.orca_init.interactive import run_interactive_flow
from multi_agent_coding_system.orca_init.cli import main

__all__ = [
    # Main entry point
    "main",
    # Analyzer
    "analyze_codebase",
    "CodebaseAnalysis",
    "FileStats",
    # Detector
    "detect_patterns",
    "PatternDetectionResult",
    "DetectedPattern",
    "VocabularyTerm",
    # Generator
    "generate_orca_config",
    # Interactive
    "run_interactive_flow",
]
