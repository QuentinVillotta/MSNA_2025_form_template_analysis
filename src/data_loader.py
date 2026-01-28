"""Load extracted data from parquet files."""

from pathlib import Path
from typing import Tuple

import pandas as pd


def load_data(data_dir: str = "data/raw") -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load extracted data from parquet files.
    
    Args:
        data_dir: Directory containing parquet files
        
    Returns:
        Tuple of (assets_df, survey_df, choices_df)
        
    Raises:
        FileNotFoundError: If data files don't exist
    """
    data_path = Path(data_dir)
    
    if not data_path.exists():
        raise FileNotFoundError(
            f"Data directory not found: {data_dir}\n"
            "Run 'uv run python scripts/extract_data.py' first"
        )
    
    assets_df = pd.read_parquet(data_path / "assets.parquet")
    survey_df = pd.read_parquet(data_path / "survey.parquet")
    choices_df = pd.read_parquet(data_path / "choices.parquet")
    
    return assets_df, survey_df, choices_df
