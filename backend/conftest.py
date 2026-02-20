"""Root conftest — ensures backend/ is on sys.path for test imports."""

import os
import sys

# Add backend directory to path so tests can import modules directly
sys.path.insert(0, os.path.dirname(__file__))
