"""Conftest for pytest configuration."""

import pytest
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_returns():
    """Sample returns for testing."""
    import numpy as np
    return np.array([0.01, 0.02, -0.01, 0.015, 0.005, 0.008, -0.002])


@pytest.fixture
def sample_prices():
    """Sample price series for testing."""
    import numpy as np
    return np.array([100, 101, 102, 101.5, 103, 104, 103])


@pytest.fixture
def sample_equity_curve():
    """Sample equity curve."""
    import numpy as np
    return [10000, 10100, 10200, 10150, 10300, 10400, 10350]
