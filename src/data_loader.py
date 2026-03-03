"""Load extracted data from parquet files."""

from pathlib import Path
from typing import Tuple

import pandas as pd
from loguru import logger


def create_display_name(row: pd.Series) -> str:
    """
    Create a readable display name for a project.
    
    Format: COUNTRY_MSNA
    Special case: For Somalia (2 projects), add HNRP or IPC suffix
    
    Args:
        row: Row from assets_df with 'country_code_settings' and 'name' columns
        
    Returns:
        Display name string (e.g., "KEN_MSNA", "SOM_MSNA_HNRP")
    """
    country_code = row['country_code_settings']
    original_name = row['name']
    
    # Base name format
    display_name = f"{country_code}_MSNA"
    
    # Special handling for Somalia - check original name for HNRP or IPC
    if country_code == 'SOM':
        if 'HNRP' in original_name.upper() or 'HNO' in original_name.upper():
            display_name = f"{country_code}_MSNA_HNRP"
        elif 'IPC' in original_name.upper():
            display_name = f"{country_code}_MSNA_IPC"
        else:
            # Fallback: try to detect from other patterns
            if 'humanitarian' in original_name.lower():
                display_name = f"{country_code}_MSNA_HNRP"
            else:
                display_name = f"{country_code}_MSNA_IPC"
    
    return display_name


def apply_data_corrections(
    assets_df: pd.DataFrame,
    survey_df: pd.DataFrame,
    choices_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Apply data corrections to loaded data.
    
    Corrections applied:
    1. Filter out specific projects that should be excluded
    2. Fix country codes for specific projects
    
    Args:
        assets_df: Assets DataFrame
        survey_df: Survey DataFrame
        choices_df: Choices DataFrame
        
    Returns:
        Tuple of corrected (assets_df, survey_df, choices_df)
    """
    # Projects to exclude
    EXCLUDED_UIDS = [
        'ammGxyDoSNd8V2JEvVuUoS',  # MSNA_2025_KI
        'aA92YScayJLNUjkxBVQWWE',  # AFG2305_MSNA_WoAA_2025 (2)
    ]
    
    # Country corrections
    COUNTRY_CORRECTIONS = {
        'ak5iQFpNGQpXcgGRrpEKjN': 'KEN',  # REACH_KEN_2025_MSNA: SOM -> KEN
    }
    
    # Filter out excluded projects
    n_assets_before = len(assets_df)
    assets_df = assets_df[~assets_df['uid'].isin(EXCLUDED_UIDS)].copy()
    n_excluded = n_assets_before - len(assets_df)
    if n_excluded > 0:
        logger.info(f"Excluded {n_excluded} projects from assets")
    
    n_survey_before = len(survey_df)
    survey_df = survey_df[~survey_df['asset_uid'].isin(EXCLUDED_UIDS)].copy()
    n_excluded_survey = n_survey_before - len(survey_df)
    if n_excluded_survey > 0:
        logger.info(f"Excluded {n_excluded_survey} survey rows")
    
    n_choices_before = len(choices_df)
    choices_df = choices_df[~choices_df['asset_uid'].isin(EXCLUDED_UIDS)].copy()
    n_excluded_choices = n_choices_before - len(choices_df)
    if n_excluded_choices > 0:
        logger.info(f"Excluded {n_excluded_choices} choices rows")
    
    # Apply country corrections
    for uid, correct_country in COUNTRY_CORRECTIONS.items():
        if uid in assets_df['uid'].values:
            old_country = assets_df.loc[assets_df['uid'] == uid, 'country_code_settings'].iloc[0]
            assets_df.loc[assets_df['uid'] == uid, 'country_code_settings'] = correct_country
            logger.info(f"Corrected country for {uid}: {old_country} -> {correct_country}")
    
    # Create readable display names
    assets_df['display_name'] = assets_df.apply(create_display_name, axis=1)
    logger.info(f"Created display names for {len(assets_df)} projects")
    
    return assets_df, survey_df, choices_df


def load_data(data_dir: str = "data/raw") -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load extracted data from parquet files and apply corrections.
    
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
    
    # Apply data corrections
    assets_df, survey_df, choices_df = apply_data_corrections(
        assets_df, survey_df, choices_df
    )
    
    return assets_df, survey_df, choices_df
