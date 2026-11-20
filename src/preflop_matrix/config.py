"""Where the theory ranges come from when --ranges is not given.

Order: --ranges  >  $PREFLOP_MATRIX_RANGES  >  $XDG_CONFIG_HOME/preflop-matrix/ranges (default ~/.config/preflop-matrix/ranges).
The first source that is set wins; a missing folder there is an error (no fall-through).
The default folder lives outside the repository, so personal or licensed ranges never get committed.
"""
import os
from pathlib import Path
from typing import NamedTuple

ENV_VAR = "PREFLOP_MATRIX_RANGES"


class RangesSource(NamedTuple):
    path: Path
    origin: str  # 參數 --ranges | 環境變數 | 預設資料夾


def default_ranges_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    base = Path(xdg).expanduser() if xdg and Path(xdg).expanduser().is_absolute() else Path.home() / ".config"
    return base / "preflop-matrix" / "ranges"


def resolve_ranges_dir(cli_value: str | None) -> RangesSource:
    if cli_value is not None:
        return RangesSource(Path(cli_value).expanduser(), "參數 --ranges")
    if env := os.environ.get(ENV_VAR):
        return RangesSource(Path(env).expanduser(), f"環境變數 {ENV_VAR}")
    return RangesSource(default_ranges_dir(), "預設資料夾")
