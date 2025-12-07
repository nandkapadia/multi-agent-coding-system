"""Per-agent model configuration for the multi-agent coding system.

This module provides model selection configuration for different agent types,
allowing the use of specialized models for different tasks (e.g., Codex-like
models for coding/review, lighter models for orchestration).

Environment Variables:
    ORCA_ORCHESTRATOR_MODEL: Model for the orchestrator agent
    ORCA_EXPLORER_MODEL: Model for explorer agents
    ORCA_CODER_MODEL: Model for coder agents
    ORCA_REVIEWER_MODEL: Model for code reviewer agents
    ORCA_TEST_WRITER_MODEL: Model for test writer agents
    LITELLM_MODEL: Fallback model if agent-specific model is not set
"""

import os
import threading
from dataclasses import dataclass, field
from typing import Optional

# Lock for thread-safe singleton initialization
_model_config_lock = threading.Lock()


@dataclass
class ModelConfig:
    """Configuration for per-agent model selection.

    Each agent type can have its own model configured via environment variables.
    If a specific model is not set, it falls back to LITELLM_MODEL.

    Example configurations:
        - Orchestrator: general model (good at planning, cost-effective)
        - Explorer: small/cheap reasoning model
        - Coder: Codex-style coding model
        - Code Reviewer: strong Codex model for thorough review
        - Test Writer: coding model for test generation
    """

    orchestrator: str = field(
        default_factory=lambda: os.getenv("ORCA_ORCHESTRATOR_MODEL", "")
    )
    explorer: str = field(
        default_factory=lambda: os.getenv("ORCA_EXPLORER_MODEL", "")
    )
    coder: str = field(
        default_factory=lambda: os.getenv("ORCA_CODER_MODEL", "")
    )
    code_reviewer: str = field(
        default_factory=lambda: os.getenv("ORCA_REVIEWER_MODEL", "")
    )
    test_writer: str = field(
        default_factory=lambda: os.getenv("ORCA_TEST_WRITER_MODEL", "")
    )

    def get_model_for_agent(self, agent_type: str) -> Optional[str]:
        """Get the configured model for a specific agent type.

        Args:
            agent_type: The type of agent (e.g., "orchestrator", "explorer",
                       "coder", "code_reviewer", "test_writer")

        Returns:
            The configured model name, or None if not configured
            (caller should fall back to LITELLM_MODEL)
        """
        model_map = {
            "orchestrator": self.orchestrator,
            "explorer": self.explorer,
            "coder": self.coder,
            "code_reviewer": self.code_reviewer,
            "test_writer": self.test_writer,
        }

        model = model_map.get(agent_type, "")
        return model if model else None


# Global singleton instance
_model_config: Optional[ModelConfig] = None


def get_model_config() -> ModelConfig:
    """Get the global model configuration instance.

    Thread-safe singleton pattern with double-checked locking.

    Returns:
        The ModelConfig singleton instance
    """
    global _model_config
    if _model_config is None:
        with _model_config_lock:
            # Double-check after acquiring lock
            if _model_config is None:
                _model_config = ModelConfig()
    return _model_config


def get_model_for_agent_type(agent_type: str) -> Optional[str]:
    """Convenience function to get model for an agent type.

    Args:
        agent_type: The type of agent

    Returns:
        The configured model name, or None if not configured
    """
    return get_model_config().get_model_for_agent(agent_type)


def reload_model_config() -> ModelConfig:
    """Reload the model configuration from environment variables.

    Thread-safe. Useful for testing or when environment variables change.

    Returns:
        The newly loaded ModelConfig instance
    """
    global _model_config
    with _model_config_lock:
        _model_config = ModelConfig()
    return _model_config
