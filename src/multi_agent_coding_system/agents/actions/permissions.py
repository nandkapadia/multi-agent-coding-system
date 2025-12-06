"""Agent permission definitions for read-only vs write-capable agent types."""

from typing import Set

# Agent type permission groups
READ_ONLY_AGENT_TYPES: Set[str] = {"explorer", "code_reviewer"}
WRITE_AGENT_TYPES: Set[str] = {"coder", "test_writer"}

# Write actions that are restricted to write-capable agents
WRITE_ACTIONS: Set[str] = {"WriteAction", "EditAction", "MultiEditAction"}

# All other actions are allowed for all agent types (read-only actions)
# This includes: ReadAction, GrepAction, GlobAction, LSAction, FileMetadataAction,
# WriteTempScriptAction, BashAction, AddNoteAction, ReportAction, etc.


def is_write_action(action_type_name: str) -> bool:
    """Check if an action type is a write action.

    Args:
        action_type_name: The name of the action type class (e.g., "WriteAction")

    Returns:
        True if the action is a write action, False otherwise
    """
    return action_type_name in WRITE_ACTIONS


def is_action_allowed_for_agent(agent_type: str, action_type_name: str) -> bool:
    """Check if an action is allowed for a given agent type.

    Args:
        agent_type: The type of agent (e.g., "explorer", "coder", "code_reviewer", "test_writer")
        action_type_name: The name of the action type class (e.g., "WriteAction")

    Returns:
        True if the action is allowed for the agent type, False otherwise
    """
    # Write actions are only allowed for write-capable agents
    if is_write_action(action_type_name):
        return agent_type in WRITE_AGENT_TYPES

    # All other actions are allowed for all agent types
    return True


def get_blocked_action_message(agent_type: str, action_type_name: str) -> str:
    """Get an error message for when an action is blocked.

    Args:
        agent_type: The type of agent that attempted the action
        action_type_name: The name of the action type that was blocked

    Returns:
        A user-friendly error message explaining why the action was blocked
    """
    return (
        f"[PERMISSION DENIED] Agent type '{agent_type}' is read-only and cannot "
        f"perform write action '{action_type_name}'. "
        f"Only agent types {WRITE_AGENT_TYPES} can perform write operations. "
        f"Read-only agents ({READ_ONLY_AGENT_TYPES}) can only use read, search, "
        f"bash, and reporting actions."
    )
