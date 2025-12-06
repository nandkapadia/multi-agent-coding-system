"""Interactive refinement flow for Orca Init.

This module provides an interactive CLI experience for refining
the generated .orca/ configuration.
"""

import os
import sys
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

from multi_agent_coding_system.orca_init.analyzer import CodebaseAnalysis, format_analysis_summary
from multi_agent_coding_system.orca_init.detector import PatternDetectionResult, format_detection_summary


# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def colorize(text: str, color: str) -> str:
    """Add color to text if terminal supports it."""
    if sys.stdout.isatty():
        return f"{color}{text}{Colors.END}"
    return text


def print_header(text: str):
    """Print a section header."""
    print()
    print(colorize(f"{'=' * 60}", Colors.CYAN))
    print(colorize(f"  {text}", Colors.BOLD + Colors.CYAN))
    print(colorize(f"{'=' * 60}", Colors.CYAN))
    print()


def print_subheader(text: str):
    """Print a subsection header."""
    print()
    print(colorize(f"--- {text} ---", Colors.YELLOW))
    print()


def print_success(text: str):
    """Print success message."""
    print(colorize(f"✓ {text}", Colors.GREEN))


def print_info(text: str):
    """Print info message."""
    print(colorize(f"ℹ {text}", Colors.BLUE))


def print_warning(text: str):
    """Print warning message."""
    print(colorize(f"⚠ {text}", Colors.YELLOW))


def print_error(text: str):
    """Print error message."""
    print(colorize(f"✗ {text}", Colors.RED))


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Prompt for yes/no answer.

    Args:
        question: Question to ask
        default: Default answer if user just presses Enter

    Returns:
        True for yes, False for no
    """
    default_str = "[Y/n]" if default else "[y/N]"
    prompt = f"{question} {default_str}: "

    while True:
        response = input(colorize(prompt, Colors.CYAN)).strip().lower()

        if not response:
            return default

        if response in ('y', 'yes'):
            return True
        if response in ('n', 'no'):
            return False

        print("Please answer 'y' or 'n'")


def prompt_text(question: str, default: str = "") -> str:
    """Prompt for text input.

    Args:
        question: Question to ask
        default: Default value if user just presses Enter

    Returns:
        User's response or default
    """
    if default:
        prompt = f"{question} [{default}]: "
    else:
        prompt = f"{question}: "

    response = input(colorize(prompt, Colors.CYAN)).strip()
    return response if response else default


def prompt_choice(question: str, choices: List[str], default: int = 0) -> int:
    """Prompt for choice from list.

    Args:
        question: Question to ask
        choices: List of choices
        default: Default choice index

    Returns:
        Index of selected choice
    """
    print(colorize(question, Colors.CYAN))
    for i, choice in enumerate(choices):
        marker = "→" if i == default else " "
        print(f"  {marker} [{i + 1}] {choice}")

    while True:
        response = input(colorize(f"Choice [1-{len(choices)}]: ", Colors.CYAN)).strip()

        if not response:
            return default

        try:
            choice = int(response) - 1
            if 0 <= choice < len(choices):
                return choice
        except ValueError:
            pass

        print(f"Please enter a number between 1 and {len(choices)}")


def prompt_multiline(question: str, hint: str = "") -> str:
    """Prompt for multiline text input.

    Args:
        question: Question to ask
        hint: Hint for how to finish input

    Returns:
        Multiline text
    """
    print(colorize(question, Colors.CYAN))
    if hint:
        print(colorize(f"  ({hint})", Colors.YELLOW))

    lines = []
    try:
        while True:
            line = input()
            if line.strip() == "":
                if lines and lines[-1].strip() == "":
                    # Two blank lines to end
                    lines.pop()
                    break
            lines.append(line)
    except EOFError:
        pass

    return "\n".join(lines)


@dataclass
class InteractiveSession:
    """State for an interactive session."""
    analysis: CodebaseAnalysis
    detection: PatternDetectionResult
    user_inputs: Dict[str, Any]

    def __init__(self, analysis: CodebaseAnalysis, detection: PatternDetectionResult):
        self.analysis = analysis
        self.detection = detection
        self.user_inputs = {}


def run_interactive_flow(
    analysis: CodebaseAnalysis,
    detection: PatternDetectionResult,
) -> Dict[str, Any]:
    """Run the interactive refinement flow.

    Args:
        analysis: Codebase analysis results
        detection: Pattern detection results

    Returns:
        Dictionary of user inputs/refinements
    """
    session = InteractiveSession(analysis, detection)

    print_header("Orca Init - Project Context Generator")

    print(f"Analyzing: {colorize(analysis.root_path, Colors.BOLD)}")
    print()

    # Phase 1: Confirm basic analysis
    _phase_confirm_analysis(session)

    # Phase 2: Refine project info
    _phase_project_info(session)

    # Phase 3: Review detected patterns
    _phase_review_patterns(session)

    # Phase 4: Add custom vocabulary
    _phase_custom_vocabulary(session)

    # Phase 5: Final confirmation
    _phase_final_confirmation(session)

    return session.user_inputs


def _phase_confirm_analysis(session: InteractiveSession):
    """Phase 1: Confirm the analysis looks correct."""
    print_subheader("Phase 1: Analysis Review")

    # Show summary
    print(f"Detected {colorize(session.analysis.primary_language, Colors.GREEN)} project")
    print(f"  - Files: {session.analysis.file_stats.total_files:,}")
    print(f"  - Lines: {session.analysis.file_stats.total_lines:,}")

    if session.analysis.frameworks:
        print(f"  - Frameworks: {', '.join(session.analysis.frameworks[:5])}")

    if session.analysis.source_directories:
        print(f"  - Source dirs: {', '.join(session.analysis.source_directories[:3])}")

    if session.analysis.test_directories:
        print(f"  - Test dirs: {', '.join(session.analysis.test_directories[:3])}")

    print()

    # Show pattern summary
    if session.detection.patterns:
        print(f"Found {len(session.detection.patterns)} patterns:")
        for pattern in session.detection.patterns[:5]:
            print(f"  - {pattern.name} ({pattern.pattern_type})")
        if len(session.detection.patterns) > 5:
            print(f"  - ... and {len(session.detection.patterns) - 5} more")
    else:
        print(colorize("No patterns detected automatically.", Colors.YELLOW))

    print()

    if not prompt_yes_no("Does this analysis look correct?"):
        print_info("You can manually edit the generated files after we create them.")


def _phase_project_info(session: InteractiveSession):
    """Phase 2: Gather/refine project information."""
    print_subheader("Phase 2: Project Information")

    # Project name
    session.user_inputs["project_name"] = prompt_text(
        "Project name",
        default=session.analysis.project_name
    )

    # Description
    print()
    print("Provide a brief project description:")
    print(colorize("  (Press Enter twice to finish)", Colors.YELLOW))
    desc = prompt_multiline("", hint="Enter twice to finish")
    if desc.strip():
        session.user_inputs["description"] = desc

    print_success("Project info captured")


def _phase_review_patterns(session: InteractiveSession):
    """Phase 3: Review and refine detected patterns."""
    print_subheader("Phase 3: Pattern Review")

    if not session.detection.patterns:
        print("No patterns were automatically detected.")
        if prompt_yes_no("Would you like to add patterns manually?", default=False):
            _add_manual_patterns(session)
        return

    print("The following patterns were detected:")
    print()

    patterns_to_document = []

    for i, pattern in enumerate(session.detection.patterns[:10]):
        print(f"  [{i + 1}] {colorize(pattern.name, Colors.BOLD)} ({pattern.pattern_type})")
        print(f"      {pattern.description}")
        if pattern.related_classes:
            print(f"      Related: {', '.join(pattern.related_classes[:3])}")
        print()

    print()

    # Ask which patterns to document
    if prompt_yes_no("Generate documentation for these patterns?"):
        session.user_inputs["patterns_to_document"] = [
            p.name for p in session.detection.patterns[:10]
        ]
        print_success(f"Will document {len(session.detection.patterns[:10])} patterns")
    else:
        # Let user select specific patterns
        print("Enter pattern numbers to document (comma-separated), or 'none':")
        response = input(colorize("> ", Colors.CYAN)).strip()

        if response.lower() != 'none':
            try:
                indices = [int(x.strip()) - 1 for x in response.split(",")]
                selected = [
                    session.detection.patterns[i].name
                    for i in indices
                    if 0 <= i < len(session.detection.patterns)
                ]
                session.user_inputs["patterns_to_document"] = selected
                print_success(f"Will document {len(selected)} patterns")
            except ValueError:
                print_warning("Could not parse selection, documenting all patterns")
                session.user_inputs["patterns_to_document"] = [
                    p.name for p in session.detection.patterns[:10]
                ]


def _add_manual_patterns(session: InteractiveSession):
    """Allow user to add patterns manually."""
    patterns = []

    print("Add patterns (enter blank name to finish):")

    while True:
        print()
        name = prompt_text("Pattern name (e.g., SignalMixin)")
        if not name:
            break

        pattern_type = prompt_choice(
            "Pattern type:",
            ["mixin", "base_class", "interface", "factory", "other"],
            default=0
        )

        description = prompt_text("Brief description")

        patterns.append({
            "name": name,
            "type": ["mixin", "base_class", "interface", "factory", "other"][pattern_type],
            "description": description,
        })

        print_success(f"Added pattern: {name}")

    session.user_inputs["manual_patterns"] = patterns


def _phase_custom_vocabulary(session: InteractiveSession):
    """Phase 4: Add custom vocabulary terms."""
    print_subheader("Phase 4: Domain Vocabulary")

    if session.detection.vocabulary:
        print("Detected vocabulary terms:")
        for term in session.detection.vocabulary[:10]:
            print(f"  - {term.term} ({term.occurrences} occurrences)")
        print()

    if prompt_yes_no("Would you like to add custom vocabulary terms?", default=False):
        terms = {}

        print("Add terms (enter blank term to finish):")

        while True:
            print()
            term = prompt_text("Term")
            if not term:
                break

            definition = prompt_text("Definition")
            terms[term] = definition
            print_success(f"Added: {term}")

        session.user_inputs["custom_vocabulary"] = terms


def _phase_final_confirmation(session: InteractiveSession):
    """Phase 5: Final confirmation before generating."""
    print_subheader("Phase 5: Generation")

    print("Ready to generate .orca/ directory with:")
    print(f"  - project.yaml")
    print(f"  - architecture.md")
    print(f"  - vocabulary.yaml")

    patterns = session.user_inputs.get("patterns_to_document", [])
    if patterns:
        print(f"  - patterns/ ({len(patterns)} pattern docs)")

    print()

    if not prompt_yes_no("Proceed with generation?"):
        print_warning("Generation cancelled.")
        session.user_inputs["cancelled"] = True
    else:
        session.user_inputs["confirmed"] = True
        print_success("Generation confirmed!")
