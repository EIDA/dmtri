from unittest.mock import patch
import pytest
from pathlib import Path
from textwrap import dedent
from dmtri.execution_plan import get_playbook_metadata, print_execution_plan

# Create a dummy playbook file
@pytest.fixture
def dummy_playbook(tmp_path):
    content = dedent("""
    - hosts: seed_nodes
      vars:
        description: Simulates a seedpsd data load
      tasks:
        - name: Task 1
          command: echo "doing something"
        - name: Task 2
          command: echo "still doing something"
    """)
    path = tmp_path / "playbook.yml"
    path.write_text(content)
    return path


@pytest.fixture
def malformed_playbook(tmp_path):
    path = tmp_path / "broken.yml"
    path.write_text("::: bad yaml :::")
    return path


def test_get_playbook_metadata_valid(dummy_playbook):
    meta = get_playbook_metadata(dummy_playbook)
    assert meta["hosts"] == "seed_nodes"
    assert meta["description"] == "Simulates a seedpsd data load"
    assert meta["tasks"] == ["Task 1", "Task 2"]


def test_get_playbook_metadata_malformed(tmp_path):
    malformed = tmp_path / "malformed.yml"
    malformed.write_text("- name: Bad: yaml\n: this is broken")
    result = get_playbook_metadata(str(malformed))
    assert "error" in result
    assert "mapping values are not allowed" in result["error"]


def test_get_playbook_metadata_empty(tmp_path):
    empty = tmp_path / "empty.yml"
    empty.write_text("")
    result = get_playbook_metadata(str(empty))
    assert "error" in result
    assert "Empty playbook" in result["error"]



@patch("builtins.input", return_value="y")
def test_print_execution_plan_confirms_and_runs(mock_input, dummy_playbook, capsys):
    variables = {"network": ["FR"], "type": ["data"]}
    print_execution_plan("refresh", variables, dummy_playbook)

    out = capsys.readouterr().out
    assert "Execution Plan" in out
    assert "network" in out
    assert "seed_nodes" in out
    assert "Task 1" in out


@patch("builtins.input", return_value="n")
def test_print_execution_plan_aborts_on_no(mock_input, dummy_playbook, capsys):
    variables = {"network": ["FR"], "type": ["data"]}
    with pytest.raises(SystemExit) as e:
        print_execution_plan("refresh", variables, dummy_playbook)
    out = capsys.readouterr().out
    assert "Aborted by user." in out
    assert e.value.code == 0
@patch("builtins.input", return_value="y")
def test_print_execution_plan_shows_metadata_error(mock_input, capsys):
    result = {"error": "mapping values are not allowed here"}
    print_execution_plan("run", {}, "bad.yml", metadata=result)
    captured = capsys.readouterr()
    assert "Warning" in captured.out

