import dmtri.init as init


def _patch_config(monkeypatch, tmp_path):
    """Point run_init at a throwaway config dir instead of the real ~/.config."""
    cfg = tmp_path / "config" / "dmtri"
    monkeypatch.setattr(init, "USER_CONFIG_DIR", cfg)
    return cfg


def test_run_init_creates_inventory_and_playbooks(monkeypatch, tmp_path):
    cfg = _patch_config(monkeypatch, tmp_path)
    init.run_init()
    assert (cfg / "hosts.ini").exists()
    assert (cfg / "playbooks").is_dir()
    # a known bundled playbook made it across
    assert (cfg / "playbooks" / "track.yml").exists()


def test_run_init_inventory_is_the_placeholder_example(monkeypatch, tmp_path):
    """The seeded hosts.ini must be the placeholder example, never real creds."""
    cfg = _patch_config(monkeypatch, tmp_path)
    init.run_init()
    text = (cfg / "hosts.ini").read_text()
    assert "<PASSWORD>" in text
    assert "<USER>" in text


def test_run_init_existing_dir_without_force_leaves_user_inventory_untouched(
    monkeypatch, tmp_path
):
    """A pre-existing config dir short-circuits: the user's edited hosts.ini is safe."""
    cfg = _patch_config(monkeypatch, tmp_path)
    cfg.mkdir(parents=True)
    (cfg / "hosts.ini").write_text("REAL SECRET INVENTORY")

    init.run_init()  # no force

    assert (cfg / "hosts.ini").read_text() == "REAL SECRET INVENTORY"
    # documents current behavior: nothing else is copied when the dir already exists
    assert not (cfg / "playbooks").exists()


def test_run_init_force_overwrites_inventory(monkeypatch, tmp_path):
    cfg = _patch_config(monkeypatch, tmp_path)
    init.run_init()
    (cfg / "hosts.ini").write_text("TAMPERED")

    init.run_init(force=True)

    assert "<PASSWORD>" in (cfg / "hosts.ini").read_text()


def test_run_init_force_overwrites_playbooks(monkeypatch, tmp_path):
    cfg = _patch_config(monkeypatch, tmp_path)
    init.run_init()
    pb = cfg / "playbooks" / "track.yml"
    pb.write_text("TAMPERED")

    init.run_init(force=True)

    assert pb.read_text() != "TAMPERED"
