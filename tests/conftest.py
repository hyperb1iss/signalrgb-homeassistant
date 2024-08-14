"""Pytest configuration file for the tests directory."""

# pylint: disable=unused-argument

import os
import sys
from pathlib import Path

import pytest

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add the custom_components directory to the Home Assistant component search path
os.environ["CUSTOM_COMPONENTS"] = str(project_root / "custom_components")

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in Home Assistant."""
    yield
