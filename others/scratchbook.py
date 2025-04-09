from pathlib import Path
import json
config_file_path = Path(__file__).parent.parent/'config.json'
project_root = Path(__file__).parent
if not config_file_path.exists():
    raise FileNotFoundError(f"Configuration file not found: {config_file_path}")
try:
    with open(config_file_path, 'r') as f:
        config = json.load(f)
except json.JSONDecodeError as e:
    raise ValueError(f"Error decoding JSON from {config_file_path}: {e}")

