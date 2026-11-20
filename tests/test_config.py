from pathlib import Path

from preflop_matrix.config import default_ranges_dir, resolve_ranges_dir


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("PREFLOP_MATRIX_RANGES", raising=False)


def test_default_falls_back_to_home_config(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    assert default_ranges_dir() == tmp_path / "home" / ".config" / "preflop-matrix" / "ranges"


def test_empty_or_relative_xdg_is_ignored(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    expected = tmp_path / "home" / ".config" / "preflop-matrix" / "ranges"
    for value in ("", "relative/dir"):
        monkeypatch.setenv("XDG_CONFIG_HOME", value)
        assert default_ranges_dir() == expected


def test_absolute_xdg_is_used(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert default_ranges_dir() == tmp_path / "xdg" / "preflop-matrix" / "ranges"


def test_order_flag_then_env_then_default(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    assert resolve_ranges_dir(None).origin == "預設資料夾"
    monkeypatch.setenv("PREFLOP_MATRIX_RANGES", "~/env-ranges")
    src = resolve_ranges_dir(None)
    assert src.origin.startswith("環境變數") and src.path == tmp_path / "home" / "env-ranges"
    assert resolve_ranges_dir("/flag").path == Path("/flag")


def test_empty_flag_is_not_treated_as_missing(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("PREFLOP_MATRIX_RANGES", "/env")
    assert resolve_ranges_dir("").origin == "參數 --ranges"
