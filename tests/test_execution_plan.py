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


def test_get_playbook_metadata_malformed(malformed_playbook):
    meta = get_playbook_metadata(malformed_playbook)
    assert "error" in meta
    assert "Failed to parse playbook" in meta["error"]


def test_get_playbook_metadata_empty(tmp_path):
    empty_playbook = tmp_path / "empty.yml"
    empty_playbook.write_text("[]")
    meta = get_playbook_metadata(empty_playbook)
    assert "error" in meta
    assert "malformed" in meta["error"]


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
def test_print_execution_plan_shows_metadata_error(tmp_path, capsys):
    # Create a broken YAML file
    broken_playbook = tmp_path / "broken.yml"
    broken_playbook.write_text(":::: not valid yaml ::::")

    variables = {
        "network": ["FR"],
        "station": ["CIEL"],
    }

    # Patch input to skip the prompt
    with patch("builtins.input", return_value="y"):
        print_execution_plan("refresh", variables, broken_playbook)

    out = capsys.readouterr().out
    assert "Warning" in out
    assert "Failed to parse playbook" in out