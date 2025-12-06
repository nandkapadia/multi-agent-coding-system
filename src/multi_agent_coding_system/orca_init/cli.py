"""CLI entry point for Orca Init.

Usage:
    orca-init [OPTIONS] [PATH]

    python -m multi_agent_coding_system.orca_init [OPTIONS] [PATH]

Options:
    --non-interactive, -n   Run without interactive prompts (use defaults)
    --output, -o DIR        Output directory for .orca/ (default: same as PATH)
    --verbose, -v           Enable verbose output
    --dry-run               Show what would be generated without writing files
    --help, -h              Show this help message
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from multi_agent_coding_system.orca_init.analyzer import analyze_codebase
from multi_agent_coding_system.orca_init.detector import detect_patterns
from multi_agent_coding_system.orca_init.generator import generate_orca_config
from multi_agent_coding_system.orca_init.interactive import (
    run_interactive_flow,
    print_header,
    print_success,
    print_error,
    print_info,
    print_warning,
    Colors,
    colorize,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="orca-init",
        description="Generate .orca/ project context directory for multi-agent coding system.",
        epilog="Example: orca-init /path/to/my-project",
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the project root (default: current directory)",
    )

    parser.add_argument(
        "-n", "--non-interactive",
        action="store_true",
        help="Run without interactive prompts (use detected defaults)",
    )

    parser.add_argument(
        "-o", "--output",
        metavar="DIR",
        help="Output directory for .orca/ (default: same as project path)",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output during analysis",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing .orca/ directory without prompting",
    )

    return parser


def validate_path(path: str) -> Path:
    """Validate the project path exists and is a directory."""
    project_path = Path(path).resolve()

    if not project_path.exists():
        print_error(f"Path does not exist: {project_path}")
        sys.exit(1)

    if not project_path.is_dir():
        print_error(f"Path is not a directory: {project_path}")
        sys.exit(1)

    return project_path


def check_existing_orca(output_path: Path, force: bool) -> bool:
    """Check if .orca/ already exists and handle accordingly.

    Returns:
        True if we should proceed, False if cancelled
    """
    orca_dir = output_path / ".orca"

    if orca_dir.exists():
        if force:
            print_warning(f"Overwriting existing .orca/ at {orca_dir}")
            return True

        print_warning(f".orca/ directory already exists at {orca_dir}")

        try:
            response = input(colorize("Overwrite? [y/N]: ", Colors.CYAN)).strip().lower()
            if response not in ('y', 'yes'):
                print_info("Cancelled. Existing .orca/ directory preserved.")
                return False
        except (EOFError, KeyboardInterrupt):
            print()
            print_info("Cancelled.")
            return False

    return True


def run_non_interactive(
    project_path: Path,
    output_path: Path,
    verbose: bool,
    dry_run: bool,
) -> int:
    """Run in non-interactive mode with detected defaults.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    print_header("Orca Init - Non-Interactive Mode")

    print(f"Analyzing: {colorize(str(project_path), Colors.BOLD)}")
    print()

    # Phase 1: Analyze codebase
    if verbose:
        print_info("Running codebase analysis...")

    analysis = analyze_codebase(str(project_path))

    if verbose:
        print(f"  - Detected language: {analysis.primary_language}")
        print(f"  - Total files: {analysis.file_stats.total_files:,}")
        print(f"  - Total lines: {analysis.file_stats.total_lines:,}")
        print()

    # Phase 2: Detect patterns
    if verbose:
        print_info("Detecting patterns and vocabulary...")

    detection = detect_patterns(str(project_path), analysis)

    if verbose:
        print(f"  - Patterns found: {len(detection.patterns)}")
        print(f"  - Vocabulary terms: {len(detection.vocabulary)}")
        print()

    # Phase 3: Generate config
    user_inputs = {
        "project_name": analysis.project_name,
        "confirmed": True,
        "patterns_to_document": [p.name for p in detection.patterns[:10]],
    }

    if dry_run:
        print_info("Dry run - would generate the following files:")
        print(f"  - {output_path}/.orca/project.yaml")
        print(f"  - {output_path}/.orca/architecture.md")
        print(f"  - {output_path}/.orca/vocabulary.yaml")
        if detection.patterns:
            print(f"  - {output_path}/.orca/patterns/ ({len(detection.patterns[:10])} files)")
        print()
        print_success("Dry run complete. No files written.")
        return 0

    if verbose:
        print_info("Generating .orca/ directory...")

    generated_files = generate_orca_config(
        str(output_path),
        analysis,
        detection,
        user_inputs,
    )

    print()
    print_success(f"Generated {len(generated_files)} files in {output_path}/.orca/")

    if verbose:
        for f in generated_files:
            print(f"  - {f}")

    return 0


def run_interactive(
    project_path: Path,
    output_path: Path,
    verbose: bool,
    dry_run: bool,
) -> int:
    """Run in interactive mode with user prompts.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Phase 1: Analyze codebase
    print_info("Analyzing codebase structure...")
    analysis = analyze_codebase(str(project_path))

    # Phase 2: Detect patterns
    print_info("Detecting patterns and conventions...")
    detection = detect_patterns(str(project_path), analysis)

    # Phase 3: Interactive refinement
    try:
        user_inputs = run_interactive_flow(analysis, detection)
    except (EOFError, KeyboardInterrupt):
        print()
        print_info("Cancelled by user.")
        return 1

    # Check if user cancelled
    if user_inputs.get("cancelled"):
        return 1

    if not user_inputs.get("confirmed"):
        print_warning("Generation not confirmed.")
        return 1

    # Phase 4: Generate config
    if dry_run:
        print()
        print_info("Dry run - would generate the following files:")
        print(f"  - {output_path}/.orca/project.yaml")
        print(f"  - {output_path}/.orca/architecture.md")
        print(f"  - {output_path}/.orca/vocabulary.yaml")
        patterns = user_inputs.get("patterns_to_document", [])
        if patterns:
            print(f"  - {output_path}/.orca/patterns/ ({len(patterns)} files)")
        print()
        print_success("Dry run complete. No files written.")
        return 0

    print()
    print_info("Generating .orca/ directory...")

    generated_files = generate_orca_config(
        str(output_path),
        analysis,
        detection,
        user_inputs,
    )

    print()
    print_success(f"Generated {len(generated_files)} files:")
    for f in generated_files:
        rel_path = os.path.relpath(f, output_path)
        print(f"  - {rel_path}")

    print()
    print_info("You can now edit these files to customize your project context.")
    print_info("Agents will automatically load this context when working on your project.")

    return 0


def main(args: Optional[list] = None) -> int:
    """Main entry point.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = create_parser()
    parsed = parser.parse_args(args)

    # Validate project path
    project_path = validate_path(parsed.path)

    # Determine output path
    if parsed.output:
        output_path = Path(parsed.output).resolve()
        if not output_path.exists():
            try:
                output_path.mkdir(parents=True)
            except OSError as e:
                print_error(f"Cannot create output directory: {e}")
                return 1
    else:
        output_path = project_path

    # Check for existing .orca/
    if not parsed.dry_run:
        if not check_existing_orca(output_path, parsed.force):
            return 0

    # Run appropriate mode
    try:
        if parsed.non_interactive:
            return run_non_interactive(
                project_path,
                output_path,
                parsed.verbose,
                parsed.dry_run,
            )
        else:
            return run_interactive(
                project_path,
                output_path,
                parsed.verbose,
                parsed.dry_run,
            )
    except Exception as e:
        print_error(f"Error: {e}")
        if parsed.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
