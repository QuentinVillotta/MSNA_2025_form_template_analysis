"""Configuration loader for project settings."""

from pathlib import Path

import yaml


def load_project_uids(config_path: str = "config/projects.yml") -> list[str]:
    """
    Load project UIDs from YAML config file.
    
    Args:
        config_path: Path to config file relative to project root
        
    Returns:
        List of asset UIDs
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    return config.get("asset_uids", [])
