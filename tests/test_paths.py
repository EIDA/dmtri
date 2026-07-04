import pytest

import dmtri.paths as paths


# --------------------------------------------------------------------------- #
# get_inventory_path priority: override > env var > user config > dev fallback
# --------------------------------------------------------------------------- #
def test_override_existing_file_is_used(tmp_path):
    p = tmp_path / "custom.ini"
    p.write_text("[nodes]\n")
    assert paths.get_inventory_path(str(p)) == p.resolve()


def test_override_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit) as e:
        paths.get_inventory_path(str(tmp_path / "nope.ini"))
    assert e.value.code == 1


def test_env_var_used_when_no_override(tmp_path, monkeypatch):
    p = tmp_path / "env.ini"
    p.write_text("[nodes]\n")
    monkeypatch.setenv("DMTRI_INVENTORY", str(p))
    assert paths.get_inventory_path() == p.resolve()


def test_env_var_pointing_at_missing_file_exits(tmp_path, monkeypatch):
    monkeypatch.setenv("DMTRI_INVENTORY", str(tmp_path / "gone.ini"))
    with pytest.raises(SystemExit) as e:
        paths.get_inventory_path()
    assert e.value.code == 1


def test_user_config_inventory_used(tmp_path, monkeypatch):
    monkeypatch.delenv("DMTRI_INVENTORY", raising=False)
    user_cfg = tmp_path / "cfg"
    user_cfg.mkdir()
    (user_cfg / "hosts.ini").write_text("[nodes]\n")
    monkeypatch.setattr(paths, "USER_CONFIG_DIR", user_cfg)
    assert paths.get_inventory_path() == user_cfg / "hosts.ini"


def test_no_inventory_anywhere_exits_with_hint(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("DMTRI_INVENTORY", raising=False)
    monkeypatch.setattr(paths, "USER_CONFIG_DIR", tmp_path / "empty")
    # neutralize the local dev-clone fallback so the test is environment-independent
    monkeypatch.setattr(paths, "INVENTORY_FILE", tmp_path / "no_hosts.ini")

    with pytest.raises(SystemExit) as e:
        paths.get_inventory_path()

    assert e.value.code == 1
    assert "dmtri init" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# _resolve_playbook: user override wins over bundled default
# --------------------------------------------------------------------------- #
def test_resolve_playbook_prefers_user_override(tmp_path, monkeypatch):
    user_pb_dir = tmp_path / "playbooks"
    (user_pb_dir / "refresh").mkdir(parents=True)
    override = user_pb_dir / "refresh" / "seedpsd_refresh.yml"
    override.write_text("---\n")
    monkeypatch.setattr(paths, "USER_PLAYBOOKS_DIR", user_pb_dir)

    assert paths._resolve_playbook("refresh/seedpsd_refresh.yml") == override


def test_resolve_playbook_falls_back_to_bundled(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "USER_PLAYBOOKS_DIR", tmp_path / "no_such_dir")
    resolved = paths._resolve_playbook("track.yml")
    assert resolved == paths.PLAYBOOKS_DIR / "track.yml"
    assert resolved.exists()
