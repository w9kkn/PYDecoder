"""Test configuration and fixtures for PYDecoder tests."""

import logging
import os
import pytest
import sys

# Add the parent directory to sys.path to ensure modules can be imported correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Disable logging during tests to avoid cluttering the output
@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging messages during tests."""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)