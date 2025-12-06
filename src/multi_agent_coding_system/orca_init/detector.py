"""Pattern and vocabulary detector for Orca Init.

This module analyzes source code to detect:
- Base classes and inheritance patterns
- Mixins and composition patterns
- Domain-specific vocabulary
- Coding conventions
"""

import os
import re
import ast
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict


@dataclass
class ClassInfo:
    """Information about a class definition."""
    name: str
    file_path: str
    line_number: int
    bases: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    methods: List[str] = field(default_factory=list)
    is_abstract: bool = False


@dataclass
class PatternInfo:
    """Information about a detected pattern."""
    name: str
    pattern_type: str  # "mixin", "base_class", "interface", "factory", etc.
    description: str
    example_files: List[str] = field(default_factory=list)
    related_classes: List[str] = field(default_factory=list)
    conventions: List[str] = field(default_factory=list)


@dataclass
class VocabularyTerm:
    """A detected domain vocabulary term."""
    term: str
    occurrences: int = 0
    contexts: List[str] = field(default_factory=list)  # File paths where found
    likely_meaning: str = ""


@dataclass
class PatternDetectionResult:
    """Results of pattern detection."""
    classes: List[ClassInfo] = field(default_factory=list)
    patterns: List[PatternInfo] = field(default_factory=list)
    vocabulary: List[VocabularyTerm] = field(default_factory=list)
    conventions: Dict[str, str] = field(default_factory=dict)


# Common pattern indicators
MIXIN_PATTERNS = [
    r"Mixin$",
    r"^Mixin",
    r"Able$",  # e.g., Serializable
]

BASE_CLASS_PATTERNS = [
    r"^Base",
    r"^Abstract",
    r"Base$",
    r"ABC$",
]

INTERFACE_PATTERNS = [
    r"^I[A-Z]",  # e.g., IRepository
    r"Interface$",
    r"Protocol$",
]

# Domain-specific term patterns (common in trading/finance)
DOMAIN_TERM_PATTERNS = {
    "trading": [
        r"order", r"trade", r"position", r"portfolio",
        r"signal", r"strategy", r"backtest",
        r"execution", r"broker", r"market",
        r"price", r"volume", r"tick",
        r"bid", r"ask", r"spread",
        r"long", r"short", r"fill",
    ],
    "web": [
        r"controller", r"service", r"repository",
        r"handler", r"middleware", r"router",
        r"request", r"response", r"session",
        r"authentication", r"authorization",
    ],
    "data": [
        r"pipeline", r"transform", r"loader",
        r"processor", r"validator", r"serializer",
        r"schema", r"model", r"entity",
    ],
}


def detect_patterns(root_path: str, languages: List[str]) -> PatternDetectionResult:
    """Detect patterns, vocabulary, and conventions in the codebase.

    Args:
        root_path: Path to the project root
        languages: List of detected languages

    Returns:
        PatternDetectionResult with all findings
    """
    root = Path(root_path)
    result = PatternDetectionResult()

    # Analyze based on language
    if "Python" in languages:
        _analyze_python(root, result)

    if any(lang in languages for lang in ["TypeScript", "JavaScript"]):
        _analyze_javascript(root, result)

    # Detect domain vocabulary
    _detect_vocabulary(root, result)

    # Identify patterns from classes
    _identify_patterns(result)

    return result


def _analyze_python(root: Path, result: PatternDetectionResult):
    """Analyze Python source files."""
    for py_file in root.rglob("*.py"):
        # Skip test files for pattern detection
        if "test" in py_file.parts or py_file.name.startswith("test_"):
            continue

        # Skip virtual environments and cache
        if any(part in str(py_file) for part in ["venv", ".venv", "__pycache__", "site-packages"]):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)
            rel_path = str(py_file.relative_to(root))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = _extract_python_class(node, rel_path)
                    result.classes.append(class_info)

        except (SyntaxError, UnicodeDecodeError):
            continue


def _extract_python_class(node: ast.ClassDef, file_path: str) -> ClassInfo:
    """Extract information from a Python class definition."""
    bases = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            bases.append(f"{_get_attr_name(base)}")

    methods = [
        item.name for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    docstring = ast.get_docstring(node)

    is_abstract = (
        "ABC" in bases or
        "abc.ABC" in bases or
        any("abstract" in m.lower() for m in methods)
    )

    return ClassInfo(
        name=node.name,
        file_path=file_path,
        line_number=node.lineno,
        bases=bases,
        docstring=docstring,
        methods=methods,
        is_abstract=is_abstract,
    )


def _get_attr_name(node: ast.Attribute) -> str:
    """Get the full name from an Attribute node."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _analyze_javascript(root: Path, result: PatternDetectionResult):
    """Analyze JavaScript/TypeScript files for patterns."""
    # Simple regex-based detection for JS/TS
    class_pattern = re.compile(
        r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?',
        re.MULTILINE
    )

    for ext in [".js", ".ts", ".tsx", ".jsx"]:
        for js_file in root.rglob(f"*{ext}"):
            # Skip test files and node_modules
            if "test" in js_file.parts or "node_modules" in js_file.parts:
                continue
            if js_file.name.endswith((".test.ts", ".test.js", ".spec.ts", ".spec.js")):
                continue

            try:
                with open(js_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                rel_path = str(js_file.relative_to(root))

                for match in class_pattern.finditer(content):
                    class_name = match.group(1)
                    base_class = match.group(2)
                    interfaces = match.group(3)

                    bases = []
                    if base_class:
                        bases.append(base_class)
                    if interfaces:
                        bases.extend([i.strip() for i in interfaces.split(",")])

                    result.classes.append(ClassInfo(
                        name=class_name,
                        file_path=rel_path,
                        line_number=content[:match.start()].count('\n') + 1,
                        bases=bases,
                    ))

            except (UnicodeDecodeError, IOError):
                continue


def _detect_vocabulary(root: Path, result: PatternDetectionResult):
    """Detect domain-specific vocabulary from the codebase."""
    term_counts: Dict[str, int] = defaultdict(int)
    term_contexts: Dict[str, Set[str]] = defaultdict(set)

    # Collect terms from class names
    for cls in result.classes:
        # Split camelCase and PascalCase
        words = re.findall(r'[A-Z][a-z]+|[a-z]+', cls.name)
        for word in words:
            word_lower = word.lower()
            term_counts[word_lower] += 1
            term_contexts[word_lower].add(cls.file_path)

    # Check for domain-specific terms
    detected_domains = set()
    for domain, patterns in DOMAIN_TERM_PATTERNS.items():
        for term in term_counts:
            if any(re.search(p, term, re.I) for p in patterns):
                detected_domains.add(domain)

    # Filter to significant terms (appear multiple times)
    for term, count in sorted(term_counts.items(), key=lambda x: -x[1]):
        if count >= 2 and len(term) > 2:
            result.vocabulary.append(VocabularyTerm(
                term=term,
                occurrences=count,
                contexts=list(term_contexts[term])[:5],  # Limit contexts
            ))


def _identify_patterns(result: PatternDetectionResult):
    """Identify patterns from collected class information."""
    # Group classes by suffix/prefix patterns
    mixin_classes = []
    base_classes = []
    interface_classes = []

    for cls in result.classes:
        name = cls.name

        # Check for mixin pattern
        if any(re.search(p, name) for p in MIXIN_PATTERNS):
            mixin_classes.append(cls)

        # Check for base class pattern
        if any(re.search(p, name) for p in BASE_CLASS_PATTERNS) or cls.is_abstract:
            base_classes.append(cls)

        # Check for interface pattern
        if any(re.search(p, name) for p in INTERFACE_PATTERNS):
            interface_classes.append(cls)

    # Create pattern entries for discovered patterns
    if mixin_classes:
        # Group mixins by common suffix
        mixin_groups = _group_by_suffix(mixin_classes, "Mixin")
        for group_name, classes in mixin_groups.items():
            result.patterns.append(PatternInfo(
                name=group_name,
                pattern_type="mixin",
                description=f"Mixin pattern for {group_name.replace('Mixin', '')} functionality",
                example_files=[c.file_path for c in classes[:3]],
                related_classes=[c.name for c in classes],
            ))

    if base_classes:
        for cls in base_classes:
            # Find classes that inherit from this
            inheritors = [c for c in result.classes if cls.name in c.bases]
            if inheritors:
                result.patterns.append(PatternInfo(
                    name=cls.name,
                    pattern_type="base_class",
                    description=f"Base class with {len(inheritors)} implementations",
                    example_files=[cls.file_path],
                    related_classes=[c.name for c in inheritors[:5]],
                ))


def _group_by_suffix(classes: List[ClassInfo], suffix: str) -> Dict[str, List[ClassInfo]]:
    """Group classes by a common suffix pattern."""
    groups: Dict[str, List[ClassInfo]] = defaultdict(list)

    for cls in classes:
        if cls.name.endswith(suffix):
            # Extract the type before the suffix
            type_name = cls.name[:-len(suffix)]
            groups[f"{type_name}{suffix}"].append(cls)
        else:
            groups[cls.name].append(cls)

    return dict(groups)


def format_detection_summary(result: PatternDetectionResult) -> str:
    """Format detection results as a human-readable summary."""
    lines = [
        "# Pattern Detection Results",
        "",
        f"## Classes Found: {len(result.classes)}",
        "",
    ]

    if result.patterns:
        lines.append("## Detected Patterns")
        for pattern in result.patterns:
            lines.append(f"\n### {pattern.name} ({pattern.pattern_type})")
            lines.append(f"{pattern.description}")
            if pattern.example_files:
                lines.append(f"- Example: {pattern.example_files[0]}")
            if pattern.related_classes:
                lines.append(f"- Related: {', '.join(pattern.related_classes[:5])}")
        lines.append("")

    if result.vocabulary:
        lines.append("## Domain Vocabulary")
        lines.append("Terms appearing frequently in the codebase:")
        for term in result.vocabulary[:20]:  # Top 20 terms
            lines.append(f"- **{term.term}** ({term.occurrences} occurrences)")
        lines.append("")

    return "\n".join(lines)
