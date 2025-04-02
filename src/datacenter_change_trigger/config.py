import tomli
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "datacenter-change-trigger" / "config.toml"

def load_config(config_path=None):
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    if not path.exists():
        print(f"Warning: Config file not found at {path}. Using default .")
        return {"endpoints": {"NOA" : "https://eida.gein.noa.gr"}}

    try:
        with open(path, "rb") as f:
            config = tomli.load(f)
    except tomli.TOMLDecodeError as e:
        raise ValueError(f"Failed to parse config file at {path}\nReason: {e}")

    if "endpoints" not in config or not isinstance(config["endpoints"], dict) or not config["endpoints"]:
        raise ValueError(f"Missing or invalid [endpoints] section in {path}")

    return config
