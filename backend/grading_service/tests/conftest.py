"""
Pytest configuration for grading_service tests.

This file ensures the project root is in the Python path so that
imports like `from schemas.grading_result import ...` work correctly.
"""
import os
import sys
from pathlib import Path

# IMPORTANT: Set TESTING=1 BEFORE importing any app modules
# This disables rate limiting and other test-unfriendly features
os.environ["TESTING"] = "1"

# Add the grading_service root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


