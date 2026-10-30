import json
import os
from pathlib import Path

from daxxl.defs import ROOT_DIR


def load_solder_config(path: Path = ROOT_DIR / "solder.json") -> dict[str, str]:
    """Create missing config with blank fields; preserve existing settings and keep secrets out of errors."""
    defaults = {key: os.environ.get(f"SOLDER_{key.upper()}", "") for key in ("url", "pack", "token")}
    allowed_fields = defaults.keys() | {"minecraft", "forge", "min_java", "java_runtime", "min_memory", "requests_per_minute"}
    try:
        try:
            with path.open("x", encoding="utf-8") as file:
                json.dump(dict.fromkeys(defaults, ""), file, indent=2)
                file.write("\n")
        except FileExistsError:
            pass
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError(f"Cannot create or read Solder configuration {path}. Check file permissions and UTF-8 JSON syntax.") from None
    if not isinstance(data, dict) or not data.keys() <= allowed_fields or any(not isinstance(value, str) for value in data.values()):
        raise ValueError(f"Invalid Solder configuration {path}. Expected a JSON object with string fields: {', '.join(sorted(allowed_fields))}.")
    return defaults | {key: value.strip() for key, value in data.items()}
