import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


# a fresh empty folder for one test, removed afterwards
@pytest.fixture
def workdir() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as folder:
        yield Path(folder)
