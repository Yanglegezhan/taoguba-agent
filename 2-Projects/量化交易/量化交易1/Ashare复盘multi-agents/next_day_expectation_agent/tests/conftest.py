"""
Pytest configuration for LLM tests
"""

import sys
from pathlib import Path

# Remove src from path if it exists to ensure we use the installed package
src_path = str(Path(__file__).parent.parent / "src")
if src_path in sys.path:
    sys.path.remove(src_path)
