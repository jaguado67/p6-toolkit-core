from pathlib import Path
import pytest
from p6toolkit import parse_xer_file, build_snapshot

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

@pytest.fixture
def baseline():
    return build_snapshot(parse_xer_file(EXAMPLES / "BL_DEMO.xer"))

@pytest.fixture
def update():
    return build_snapshot(parse_xer_file(EXAMPLES / "UP01_DEMO.xer"))
