"""Local filesystem command executor for IDE integration.

This executor runs commands directly in the local filesystem,
making it suitable for MCP integration with VS Code/Cursor.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Tuple

from multi_agent_coding_system.agents.env_interaction.command_executor import (
    CommandExecutor
)

logger = logging.getLogger(__name__)


class LocalFilesystemExecutor(CommandExecutor):
    """Execute commands in the local filesystem workspace.
    
    This executor is designed for IDE integration where the agent
    works directly with the user's workspace files.
    
    Args:
        workspace_root: Root directory of the workspace (default: current dir)
        timeout: Default timeout for commands in seconds
    """
    
    def __init__(self, workspace_root: str = None, timeout: int = 30):
        """Initialize local filesystem executor.
        
        Args:
            workspace_root: Root directory for workspace (default: current dir)
            timeout: Default command timeout in seconds
        """
        if workspace_root:
            self.workspace_root = Path(workspace_root).resolve()
        else:
            # Default to current working directory
            self.workspace_root = Path.cwd().resolve()
        
        if not self.workspace_root.exists():
            raise ValueError(f"Workspace root does not exist: {self.workspace_root}")
        
        if not self.workspace_root.is_dir():
            raise ValueError(f"Workspace root is not a directory: {self.workspace_root}")
        
        self.default_timeout = timeout
        logger.info(f"LocalFilesystemExecutor initialized with workspace: {self.workspace_root}")
    
    async def execute(self, cmd: str, timeout: int = None) -> Tuple[str, int]:
        """Execute a command in the workspace directory.
        
        Commands are executed in the workspace root directory.
        The command is run using bash -c for shell features.
        
        Args:
            cmd: Command to execute
            timeout: Timeout in seconds (uses default if not specified)
            
        Returns:
            Tuple of (output, exit_code)
        """
        timeout = timeout or self.default_timeout
        
        try:
            # Change to workspace directory for execution
            proc = await asyncio.create_subprocess_exec(
                'bash', '-c', cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(self.workspace_root)
            )
            
            try:
                stdout, _ = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
                output = stdout.decode('utf-8', errors='replace') if stdout else ""
                exit_code = proc.returncode or 0
                return output, exit_code
                
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return (
                    f"Command timed out after {timeout} seconds",
                    124  # Standard timeout exit code
                )
                
        except Exception as e:
            error_msg = f"Error executing command: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg, 1
    
    async def execute_background(self, cmd: str) -> None:
        """Execute a command in background.
        
        Note: Background commands are fire-and-forget.
        Errors are logged but not raised.
        
        Args:
            cmd: Command to execute in background
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                'bash', '-c', f"nohup {cmd} > /dev/null 2>&1 &",
                cwd=str(self.workspace_root),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            # Wait briefly to catch immediate failures
            try:
                await asyncio.wait_for(proc.wait(), timeout=0.1)
                if proc.returncode != 0:
                    logger.warning(
                        f"Background command may have failed: {cmd[:50]}..."
                    )
            except asyncio.TimeoutError:
                # Expected - process is running in background
                pass
                
        except Exception as e:
            logger.error(f"Failed to start background command: {e}", exc_info=True)

