"""Support both plain discovery and the existing top-level fixture imports."""
from pathlib import Path
import sys
from finscope.test_safety import activate_if_requested
activate_if_requested()
fixture_path = str(Path(__file__).resolve().parent)
if fixture_path not in sys.path:
    sys.path.insert(0, fixture_path)
