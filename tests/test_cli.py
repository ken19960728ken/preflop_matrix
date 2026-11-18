import json
import subprocess
import sys

import pytest

from helpers import calls, folds, make_hand, raises
from preflop_matrix.cli import main

RFI_REST = [folds("HJ"), folds("CO"), folds("BTN"), folds("SB")]


@pytest.fixture
def hands_dir(tmp_path):
    folder = tmp_path / "hands" / "gg"
    folder.mkdir(parents=True)
    (folder / "a.txt").write_text(
        make_hand([raises("UTG", 2)] + RFI_REST + [calls("BB")], hand_id="RC1")
        + make_hand([raises("UTG", 2)] + RFI_REST + [raises("BB", 9), folds("UTG")], hand_id="RC2"))
    (folder / "b.txt").write_text(make_hand([folds("UTG")] + RFI_REST, hand_id="RC3", hero="SB"))
    return tmp_path / "hands"


@pytest.fixture
def ranges_dir(write_ranges):
    return write_ranges({"UTG Open 2bb": {"AA": 1, "KK": 0.5}, "BB vs UTG open 2bb call": {"AA": 0.5},
                         "BB vs UTG open 2bb 3bet 9bb": {"AA": 0.5, "KK": 1}, "BB vs UTG open 2bb SB call call": {"AA": 1}})


def run(*argv):
    return main([str(a) for a in argv])


def test_end_to_end(hands_dir, ranges_dir, tmp_path, capsys):
    out, data_path = tmp_path / "out" / "m.html", tmp_path / "m.json"
    assert run("--hands", hands_dir, "--ranges", ranges_dir, "-o", out, "--json", data_path, "--title", "測試") == 0
    printed = capsys.readouterr().out
    assert "採用 3 手" in printed and "對應到節點 3 個" in printed and "忽略（多人或不認得）1" in printed
    page = out.read_text(encoding="utf-8")
    assert "<title>測試</title>" in page and "const D = {" in page
    data = json.loads(data_path.read_text(encoding="utf-8"))
    assert data["open"]["UTG"]["th"]["r"] == pytest.approx(9 / 1326)
    assert data["open"]["UTG"]["pool"] == {"r": 2 / 3, "n": 3}
    assert data["vs_open"]["UTG>BB"]["me"] == {"c": 0.5, "r": 0.5, "n": 2}
    assert data["vs_open"]["UTG>BB"]["th"]["c"] == pytest.approx(3 / 1326)
    assert data["meta"]["hands"] == 3


def test_hero_option(hands_dir, ranges_dir, tmp_path, capsys):
    data_path = tmp_path / "m.json"
    assert run("--hands", hands_dir, "--ranges", ranges_dir, "-o", tmp_path / "o.html", "--hero", "p_UTG", "--json", data_path) == 0
    utg = json.loads(data_path.read_text())["open"]["UTG"]
    assert utg["me"] == {"r": pytest.approx(2 / 3), "n": 3} and utg["pool"] is None
    assert run("--hands", hands_dir, "--ranges", ranges_dir, "-o", tmp_path / "o.html", "--hero", "Nobody") == 0
    assert "Nobody" in capsys.readouterr().err


def test_default_output_name_is_in_the_current_directory(hands_dir, ranges_dir, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert run("--hands", hands_dir, "--ranges", ranges_dir) == 0
    assert (tmp_path / "preflop_matrix.html").is_file()


def test_unparseable_and_non_six_hands_are_counted_but_not_fatal(hands_dir, ranges_dir, tmp_path, capsys):
    (hands_dir / "bad.txt").write_text(make_hand([], hand_id="RC9").replace("big blind", "huge blind"))
    assert run("--hands", hands_dir, "--ranges", ranges_dir, "-o", tmp_path / "o.html") == 0
    printed = capsys.readouterr().out
    assert "無法解析略過 1" in printed and "bad.txt" in printed


def test_ranges_without_a_matching_file_still_render(hands_dir, write_ranges, tmp_path):
    out = tmp_path / "o.html"
    assert run("--hands", hands_dir, "--ranges", write_ranges({"BB vs UTG open 2bb SB call call": {"AA": 1}}), "-o", out) == 0
    assert out.is_file()


@pytest.mark.parametrize("which", ["hands", "ranges"])
def test_missing_folder_is_exit_2(which, hands_dir, ranges_dir, tmp_path, capsys):
    args = {"hands": hands_dir, "ranges": ranges_dir}
    args[which] = tmp_path / "nope"
    assert run("--hands", args["hands"], "--ranges", args["ranges"], "-o", tmp_path / "o.html") == 2
    assert "不存在" in capsys.readouterr().err
    assert not (tmp_path / "o.html").exists()


def test_a_file_instead_of_a_folder_is_exit_2(hands_dir, ranges_dir, tmp_path, capsys):
    not_a_dir = tmp_path / "file.txt"
    not_a_dir.write_text("x")
    assert run("--hands", not_a_dir, "--ranges", ranges_dir) == 2


def test_no_hands_is_exit_1(tmp_path, ranges_dir, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert run("--hands", empty, "--ranges", ranges_dir, "-o", tmp_path / "o.html") == 1
    assert "沒有可用的手牌" in capsys.readouterr().err
    assert not (tmp_path / "o.html").exists()


def test_only_unparseable_hands_is_exit_1_with_summary(tmp_path, ranges_dir, capsys):
    folder = tmp_path / "h"
    folder.mkdir()
    (folder / "x.txt").write_text(make_hand([], hand_id="RC1").replace("big blind", "huge blind"))
    assert run("--hands", folder, "--ranges", ranges_dir, "-o", tmp_path / "o.html") == 1
    captured = capsys.readouterr()
    assert "無法解析略過 1" in captured.out and "沒有可用的手牌" in captured.err


def test_empty_ranges_folder_is_exit_1(hands_dir, tmp_path, capsys):
    empty = tmp_path / "r"
    empty.mkdir()
    assert run("--hands", hands_dir, "--ranges", empty, "-o", tmp_path / "o.html") == 1
    assert "沒有 .txt 範圍檔" in capsys.readouterr().err


def test_unwritable_output_is_exit_1(hands_dir, ranges_dir, tmp_path, capsys):
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    assert run("--hands", hands_dir, "--ranges", ranges_dir, "-o", blocker / "o.html") == 1
    assert "無法寫入" in capsys.readouterr().err


def test_missing_required_arguments_exit_2(capsys):
    with pytest.raises(SystemExit) as exc:
        run("--hands", "x")
    assert exc.value.code == 2


def test_module_entry_point_runs():
    result = subprocess.run([sys.executable, "-m", "preflop_matrix.cli", "--help"], capture_output=True, text=True)
    assert result.returncode == 0 and "--hands" in result.stdout
