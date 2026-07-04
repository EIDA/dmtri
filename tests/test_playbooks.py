"""Guard the bundled Ansible playbooks — the actual product — against syntax rot.

These are shipped in the wheel and executed on remote nodes, so a broken YAML
file would only surface at run time on a user's infrastructure. A parse check
catches it before a release tag goes out.
"""
import yaml
import pytest

from dmtri.paths import PLAYBOOKS_DIR

PLAYBOOKS = sorted(PLAYBOOKS_DIR.rglob("*.yml"))

# Intentionally-empty placeholder playbooks for not-yet-implemented `clean`
# targets. Pinned here so that (a) a real playbook accidentally emptied is
# caught, and (b) filling one of these in is a deliberate, visible change.
KNOWN_EMPTY_STUBS = {
    "clean/availability_clean.yml",
    "clean/seedpsd_clean.yml",
}


def _rel(p):
    return str(p.relative_to(PLAYBOOKS_DIR))


def test_playbooks_are_discovered():
    assert PLAYBOOKS, f"no bundled playbooks found under {PLAYBOOKS_DIR}"


@pytest.mark.parametrize("pb", PLAYBOOKS, ids=[_rel(p) for p in PLAYBOOKS])
def test_playbook_parses_without_yaml_error(pb):
    # must not raise; empty files are allowed here (see the stub test below)
    list(yaml.safe_load_all(pb.read_text()))


@pytest.mark.parametrize(
    "pb",
    [p for p in PLAYBOOKS if _rel(p) not in KNOWN_EMPTY_STUBS],
    ids=[_rel(p) for p in PLAYBOOKS if _rel(p) not in KNOWN_EMPTY_STUBS],
)
def test_populated_playbook_is_a_list_of_plays(pb):
    docs = [d for d in yaml.safe_load_all(pb.read_text()) if d is not None]
    assert docs, f"{_rel(pb)} unexpectedly parsed to no documents"
    top = docs[0]
    assert isinstance(top, list), f"{_rel(pb)} top-level is not a list of plays"
    assert all(isinstance(play, dict) for play in top), f"{_rel(pb)} has a non-mapping play"


def test_only_known_stubs_are_empty():
    """A populated playbook silently going empty is a regression, not a stub."""
    empty = {_rel(p) for p in PLAYBOOKS if not p.read_text().strip()}
    assert empty == KNOWN_EMPTY_STUBS, (
        f"empty playbooks changed: {empty ^ KNOWN_EMPTY_STUBS}"
    )
