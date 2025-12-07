#!/usr/bin/env python3
"""Example script showing how to run the orchestrator agent with a task.

Usage:
    # Set your API key
    export LITE_LLM_API_KEY="your-api-key-here"
    
    # Optionally set models
    export ORCA_ORCHESTRATOR_MODEL="anthropic/claude-sonnet-4-5-20250929"
    export ORCA_SUBAGENT_MODEL="anthropic/claude-sonnet-4-5-20250929"
    
    # Run the example
    python example_run_task.py
"""

import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path

from multi_agent_coding_system.misc.async_docker_container_manager import (
    AsyncDockerContainerManager
)
from multi_agent_coding_system.agents.env_interaction.command_executor import (
    DockerExecutor
)
from multi_agent_coding_system.agents.orchestrator_agent import OrchestratorAgent


async def run_task(instruction: str, max_turns: int = 50):
    """Run the orchestrator agent with a given task.
    
    Args:
        instruction: The task description to execute
        max_turns: Maximum number of turns (default: 50)
    """
    # Check for API key
    api_key = os.getenv("LITE_LLM_API_KEY") or os.getenv("ORCA_ORCHESTRATOR_API_KEY")
    if not api_key:
        print("ERROR: Please set LITE_LLM_API_KEY or ORCA_ORCHESTRATOR_API_KEY")
        print("Example: export LITE_LLM_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Create temporary directory for Dockerfile
    temp_dir = tempfile.mkdtemp(prefix="orchestrator_task_")
    dockerfile_content = """FROM ubuntu:latest
RUN apt-get update && apt-get install -y bash python3 python3-pip git
WORKDIR /workspace
CMD ["/bin/bash"]
"""
    
    container_id = None
    manager = AsyncDockerContainerManager()
    
    try:
        # Write Dockerfile
        dockerfile_path = Path(temp_dir) / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        
        # Start Docker container
        print("Starting Docker container...")
        await manager._ensure_initialized()
        container_id = await manager.spin_up_container_from_dir(
            build_context_dir=temp_dir,
            image_name="orchestrator_task"
        )
        print(f"Container started: {container_id[:12]}...")
        
        # Wait for container to stabilize
        await asyncio.sleep(1)
        
        # Create executor
        executor = DockerExecutor(container_id, docker_manager=manager)
        
        # Create orchestrator agent
        orchestrator = OrchestratorAgent(
            temperature=0.1,  # Lower temperature for more deterministic behavior
        )
        
        # Setup orchestrator with executor
        logging_dir = Path("./session_logs")
        orchestrator.setup(executor, logging_dir=logging_dir)
        
        # Run the task
        print(f"\n{'=' * 60}")
        print(f"Task: {instruction}")
        print(f"{'=' * 60}\n")
        
        result = await orchestrator.run(instruction, max_turns=max_turns)
        
        # Display results
        print(f"\n{'=' * 60}")
        print("EXECUTION RESULT")
        print(f"{'=' * 60}")
        print(f"Completed: {result['completed']}")
        print(f"Finish message: {result['finish_message']}")
        print(f"Turns executed: {result['turns_executed']}")
        print(f"Max turns reached: {result['max_turns_reached']}")
        print(f"{'=' * 60}\n")
        
        return result
        
    finally:
        # Clean up
        if container_id:
            print("Cleaning up container...")
            await manager.close_container(container_id)
        await manager.close()
        
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print("Cleaned up temporary files")


async def main():
    """Main entry point."""
    # Example task - modify this to your needs
    task = (
        "Create a Python script called 'hello.py' that prints 'Hello, World!' "
        "and then run it to verify it works."
    )
    
    # You can also pass a custom task via command line
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    
    await run_task(task, max_turns=50)


if __name__ == "__main__":
    asyncio.run(main())

