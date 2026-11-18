from itertools import count
from pathlib import Path

import pytest

from helpers import range_text


@pytest.fixture
def write_ranges(tmp_path):
    """Write {file stem: {hand: weight}} as range files into a fresh folder and return it."""
    folders = count()

    def _write(files: dict[str, dict[str, float]]) -> Path:
        folder = tmp_path / f"ranges{next(folders)}"
        folder.mkdir()
        for stem, weights in files.items():
            (folder / f"{stem}.txt").write_text(range_text(weights), encoding="utf-8")
        return folder
    return _write
