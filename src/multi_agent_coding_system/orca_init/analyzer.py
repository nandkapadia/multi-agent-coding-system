"""Codebase structure analyzer for Orca Init.

This module provides functions to analyze a codebase's structure,
identifying languages, frameworks, directory organization, and key files.
"""

import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from collections import Counter


@dataclass
class FileStats:
    """Statistics about files in the codebase."""
    total_files: int = 0
    total_lines: int = 0
    by_extension: Dict[str, int] = field(default_factory=dict)
    by_directory: Dict[str, int] = field(default_factory=dict)


@dataclass
class CodebaseAnalysis:
    """Complete analysis of a codebase."""
    root_path: str
    project_name: str = ""

    # Languages and frameworks
    primary_language: str = ""
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)

    # Structure
    source_directories: List[str] = field(default_factory=list)
    test_directories: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)

    # Statistics
    file_stats: FileStats = field(default_factory=FileStats)

    # Key files
    readme_path: Optional[str] = None
    package_manager_files: List[str] = field(default_factory=list)

    # Detected patterns
    base_classes: List[str] = field(default_factory=list)
    mixins: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)


# Common patterns for detection
LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".jsx": "JavaScript (React)",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
}

FRAMEWORK_INDICATORS = {
    # Python
    "requirements.txt": ["Python"],
    "pyproject.toml": ["Python"],
    "setup.py": ["Python"],
    "Pipfile": ["Python", "Pipenv"],
    "poetry.lock": ["Python", "Poetry"],
    "django": ["Django"],
    "flask": ["Flask"],
    "fastapi": ["FastAPI"],
    "pytest.ini": ["pytest"],
    "tox.ini": ["tox"],

    # JavaScript/TypeScript
    "package.json": ["Node.js"],
    "tsconfig.json": ["TypeScript"],
    "next.config": ["Next.js"],
    "nuxt.config": ["Nuxt.js"],
    "vue.config": ["Vue.js"],
    "angular.json": ["Angular"],
    "vite.config": ["Vite"],
    "vitest.config": ["Vitest"],
    "jest.config": ["Jest"],

    # Other
    "Cargo.toml": ["Rust", "Cargo"],
    "go.mod": ["Go"],
    "Gemfile": ["Ruby", "Bundler"],
    "composer.json": ["PHP", "Composer"],
    "pom.xml": ["Java", "Maven"],
    "build.gradle": ["Java/Kotlin", "Gradle"],
}

IGNORE_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".pytest_cache",
    "venv", ".venv", "env", ".env",
    "dist", "build", "target",
    ".idea", ".vscode",
    "coverage", ".coverage",
    ".orca",  # Don't analyze existing .orca
}

IGNORE_FILES = {
    ".DS_Store", "Thumbs.db",
    ".gitignore", ".gitattributes",
}


def analyze_codebase(root_path: str) -> CodebaseAnalysis:
    """Analyze a codebase and return structured information.

    Args:
        root_path: Path to the project root directory

    Returns:
        CodebaseAnalysis with all discovered information
    """
    root = Path(root_path).resolve()
    analysis = CodebaseAnalysis(root_path=str(root))

    # Get project name from directory
    analysis.project_name = root.name

    # Scan files
    extension_counts: Counter = Counter()
    dir_counts: Counter = Counter()
    total_lines = 0
    total_files = 0

    for path in _walk_codebase(root):
        rel_path = path.relative_to(root)

        # Count by extension
        ext = path.suffix.lower()
        if ext:
            extension_counts[ext] += 1

        # Count by top-level directory
        if len(rel_path.parts) > 1:
            dir_counts[rel_path.parts[0]] += 1

        # Count lines (for text files)
        if ext in LANGUAGE_EXTENSIONS:
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    total_lines += sum(1 for _ in f)
            except:
                pass

        total_files += 1

        # Check for specific files
        _check_special_files(path, rel_path, analysis)

    # Set file stats
    analysis.file_stats = FileStats(
        total_files=total_files,
        total_lines=total_lines,
        by_extension=dict(extension_counts),
        by_directory=dict(dir_counts),
    )

    # Determine languages
    _detect_languages(extension_counts, analysis)

    # Detect frameworks from files
    _detect_frameworks(root, analysis)

    # Find source and test directories
    _find_directories(root, analysis)

    # Find entry points
    _find_entry_points(root, analysis)

    return analysis


def _walk_codebase(root: Path):
    """Walk the codebase, skipping ignored directories."""
    for item in root.iterdir():
        if item.name in IGNORE_DIRS or item.name in IGNORE_FILES:
            continue

        if item.is_file():
            yield item
        elif item.is_dir():
            yield from _walk_codebase(item)


def _check_special_files(path: Path, rel_path: Path, analysis: CodebaseAnalysis):
    """Check if a file is a special/important file."""
    name = path.name.lower()

    # README
    if name.startswith("readme"):
        analysis.readme_path = str(rel_path)

    # Package manager files
    if name in {"package.json", "pyproject.toml", "requirements.txt",
                "cargo.toml", "go.mod", "gemfile", "composer.json"}:
        analysis.package_manager_files.append(str(rel_path))

    # Config files
    if name.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".cfg")):
        if "config" in name or "settings" in name:
            analysis.config_files.append(str(rel_path))


def _detect_languages(extension_counts: Counter, analysis: CodebaseAnalysis):
    """Detect programming languages from file extensions."""
    languages = []
    for ext, count in extension_counts.most_common():
        if ext in LANGUAGE_EXTENSIONS and count > 0:
            lang = LANGUAGE_EXTENSIONS[ext]
            if lang not in languages:
                languages.append(lang)

    analysis.languages = languages
    if languages:
        analysis.primary_language = languages[0]


def _detect_frameworks(root: Path, analysis: CodebaseAnalysis):
    """Detect frameworks from indicator files."""
    frameworks = set()

    for item in root.iterdir():
        name = item.name.lower()
        for indicator, fw_list in FRAMEWORK_INDICATORS.items():
            if indicator.lower() in name:
                frameworks.update(fw_list)

    # Check package.json for specific packages
    package_json = root / "package.json"
    if package_json.exists():
        try:
            import json
            with open(package_json) as f:
                pkg = json.load(f)
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            if "react" in deps:
                frameworks.add("React")
            if "vue" in deps:
                frameworks.add("Vue.js")
            if "express" in deps:
                frameworks.add("Express")
            if "fastify" in deps:
                frameworks.add("Fastify")
            if "vitest" in deps:
                frameworks.add("Vitest")
            if "jest" in deps:
                frameworks.add("Jest")
        except:
            pass

    # Check pyproject.toml for specific packages
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text()
            if "django" in content.lower():
                frameworks.add("Django")
            if "flask" in content.lower():
                frameworks.add("Flask")
            if "fastapi" in content.lower():
                frameworks.add("FastAPI")
            if "pytest" in content.lower():
                frameworks.add("pytest")
            if "pandas" in content.lower():
                frameworks.add("pandas")
            if "numpy" in content.lower():
                frameworks.add("NumPy")
        except:
            pass

    analysis.frameworks = sorted(frameworks)


def _find_directories(root: Path, analysis: CodebaseAnalysis):
    """Find source and test directories."""
    source_patterns = ["src", "lib", "app", "pkg", "internal"]
    test_patterns = ["test", "tests", "spec", "specs", "__tests__"]

    for item in root.iterdir():
        if not item.is_dir() or item.name in IGNORE_DIRS:
            continue

        name = item.name.lower()

        if any(p in name for p in test_patterns):
            analysis.test_directories.append(item.name)
        elif any(p == name for p in source_patterns):
            analysis.source_directories.append(item.name)
        elif _contains_code(item):
            # It's a code directory if it contains source files
            analysis.source_directories.append(item.name)


def _contains_code(directory: Path) -> bool:
    """Check if a directory contains code files."""
    try:
        for item in directory.iterdir():
            if item.is_file() and item.suffix in LANGUAGE_EXTENSIONS:
                return True
            if item.is_dir() and item.name not in IGNORE_DIRS:
                if _contains_code(item):
                    return True
    except PermissionError:
        pass
    return False


def _find_entry_points(root: Path, analysis: CodebaseAnalysis):
    """Find likely entry point files."""
    entry_patterns = [
        "main.py", "app.py", "__main__.py",
        "index.js", "index.ts", "main.js", "main.ts",
        "server.py", "server.js", "server.ts",
        "cli.py", "cli.js", "cli.ts",
    ]

    # Check root
    for pattern in entry_patterns:
        if (root / pattern).exists():
            analysis.entry_points.append(pattern)

    # Check src directory
    for src_dir in analysis.source_directories:
        src_path = root / src_dir
        for pattern in entry_patterns:
            if (src_path / pattern).exists():
                analysis.entry_points.append(f"{src_dir}/{pattern}")


def format_analysis_summary(analysis: CodebaseAnalysis) -> str:
    """Format the analysis as a human-readable summary."""
    lines = [
        f"# Codebase Analysis: {analysis.project_name}",
        f"",
        f"## Overview",
        f"- **Location**: {analysis.root_path}",
        f"- **Primary Language**: {analysis.primary_language or 'Unknown'}",
        f"- **Languages**: {', '.join(analysis.languages) or 'None detected'}",
        f"- **Frameworks**: {', '.join(analysis.frameworks) or 'None detected'}",
        f"",
        f"## Statistics",
        f"- **Total Files**: {analysis.file_stats.total_files:,}",
        f"- **Total Lines**: {analysis.file_stats.total_lines:,}",
        f"",
        f"## Structure",
        f"- **Source Directories**: {', '.join(analysis.source_directories) or 'None found'}",
        f"- **Test Directories**: {', '.join(analysis.test_directories) or 'None found'}",
        f"- **Entry Points**: {', '.join(analysis.entry_points) or 'None found'}",
        f"",
    ]

    if analysis.config_files:
        lines.append(f"## Config Files")
        for cf in analysis.config_files[:10]:  # Limit to 10
            lines.append(f"- {cf}")
        if len(analysis.config_files) > 10:
            lines.append(f"- ... and {len(analysis.config_files) - 10} more")
        lines.append("")

    return "\n".join(lines)
