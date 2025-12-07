import os
from pathlib import Path
from functools import lru_cache
from typing import Optional

LATEST_SYSTEM_MSGS = {
    "orchestrator": "orchestrator_sys_msg.md",
    "explorer": "explorer_sys_msg.md",
    "coder": "coder_sys_msg.md",
    "code_reviewer": "code_reviewer_sys_msg.md",
    "test_writer": "test_writer_sys_msg.md",
}

cwd = os.getcwd()
this_dir_path: Path = Path(__file__).parent.resolve()
system_msgs_dir = Path(this_dir_path) / "md_files"


@lru_cache(maxsize=None)
def _load_system_message(agent_type: str) -> str:
    """Load a system message file for the given agent type.

    Args:
        agent_type: The type of agent (e.g., "orchestrator", "explorer")

    Returns:
        The system message content as a string

    Raises:
        ValueError: If the agent type is unknown
        FileNotFoundError: If the system message file doesn't exist
    """
    if agent_type not in LATEST_SYSTEM_MSGS:
        raise ValueError(f"Unknown agent type: {agent_type}")

    file_name = LATEST_SYSTEM_MSGS[agent_type]
    file_path = system_msgs_dir / file_name

    if not file_path.exists():
        raise FileNotFoundError(f"System message file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def load_orchestrator_system_message() -> str:
    """Load the orchestrator system message."""
    return _load_system_message("orchestrator")


def load_explorer_system_message(depth: Optional[int] = None) -> str:
    """Load the explorer system message.

    Args:
        depth: Agent nesting depth (reserved for future depth-aware prompts)
    """
    # depth parameter reserved for future use (e.g., depth-specific instructions)
    return _load_system_message("explorer")


def load_coder_system_message(depth: Optional[int] = None) -> str:
    """Load the coder system message.

    Args:
        depth: Agent nesting depth (reserved for future depth-aware prompts)
    """
    return _load_system_message("coder")


def load_code_reviewer_system_message(depth: Optional[int] = None) -> str:
    """Load the code reviewer system message.

    Args:
        depth: Agent nesting depth (reserved for future depth-aware prompts)
    """
    return _load_system_message("code_reviewer")


def load_test_writer_system_message(depth: Optional[int] = None) -> str:
    """Load the test writer system message.

    Args:
        depth: Agent nesting depth (reserved for future depth-aware prompts)
    """
    return _load_system_message("test_writer")
