import pytest
import json
from pathlib import Path
from unittest.mock import patch
from datacenter_change_trigger import nodes

def test_load_nodes_returns_list():
    result = nodes.load_nodes()
    assert isinstance(result, list)
    assert all(isinstance(n, tuple) and len(n) == 3 for n in result)

def test_cache_save_and_load(tmp_path):
    original_cache_file = nodes.CACHE_FILE
    nodes.CACHE_FILE = tmp_path / "nodes_cache.json"

    sample_nodes = [
        ("TEST_NODE", "https://test.example.com/fdsnws/", True)
    ]

    nodes.save_nodes_to_cache(sample_nodes)
    loaded = nodes.load_cached_nodes()

    assert loaded == sample_nodes
    nodes.CACHE_FILE = original_cache_file

@patch("datacenter_change_trigger.nodes.CACHE_FILE")
def test_invalid_cache_removes_file(mock_cache_file, tmp_path):
    bad_file = tmp_path / "nodes_cache.json"
    bad_file.write_text("{ invalid json")

    mock_cache_file.exists.return_value = True
    mock_cache_file.open = lambda *args, **kwargs: open(bad_file, *args, **kwargs)
    mock_cache_file.unlink = lambda: bad_file.unlink()
    mock_cache_file.__str__.return_value = str(bad_file)

    result = nodes.load_cached_nodes()

    assert isinstance(result, list)
    assert not bad_file.exists()

@patch("datacenter_change_trigger.nodes.CACHE_FILE")
@patch("datacenter_change_trigger.nodes.fetch_nodes_from_api", return_value=None)
def test_invalid_cache_falls_back_to_default(mock_fetch, mock_cache_file, tmp_path):
    bad_file = tmp_path / "nodes_cache.json"
    bad_file.write_text("{ invalid json")

    mock_cache_file.exists.return_value = True
    mock_cache_file.open = lambda *args, **kwargs: open(bad_file, *args, **kwargs)
    mock_cache_file.unlink = lambda: bad_file.unlink()
    mock_cache_file.__str__.return_value = str(bad_file)

    result = nodes.load_cached_nodes()

    assert result == nodes.DEFAULT_NODES
