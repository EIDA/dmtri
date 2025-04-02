import pytest
import tempfile
from pathlib import Path
from datacenter_change_trigger import config

def test_missing_config_file_falls_back_to_default():
    result = config.load_config("/nonexistent/file.toml")
    assert result["endpoints"]["NOA"] == "https://eida.gein.noa.gr"

def test_invalid_toml_raises_value_error(tmp_path):
    bad_file = tmp_path / "bad.toml"
    bad_file.write_text("invalid = = value")
    
    with pytest.raises(ValueError, match="Failed to parse config file"):
        config.load_config(bad_file)

def test_missing_endpoints_key_raises_value_error(tmp_path):
    bad_file = tmp_path / "bad.toml"
    bad_file.write_text("""
    [fdsn]
    endpoint = "https://eida.gein.noa.gr"
    """)
    
    with pytest.raises(ValueError, match="Missing or invalid \\[endpoints\\] section"):
        config.load_config(bad_file)

def test_valid_config_loads_correctly(tmp_path):
    good_file = tmp_path / "good.toml"
    good_file.write_text("""
    [endpoints]
    NOA = "https://eida.gein.noa.gr"
    GFZ = "https://geofon.gfz.de"
    """)

    result = config.load_config(good_file)
    assert "NOA" in result["endpoints"]
    assert result["endpoints"]["GFZ"] == "https://geofon.gfz.de"
