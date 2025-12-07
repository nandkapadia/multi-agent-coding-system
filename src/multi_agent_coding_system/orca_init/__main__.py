"""Allow running orca_init as a module: python -m multi_agent_coding_system.orca_init"""

import sys
from multi_agent_coding_system.orca_init.cli import main

if __name__ == "__main__":
    sys.exit(main())
