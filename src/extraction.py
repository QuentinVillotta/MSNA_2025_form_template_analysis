"""Extract and save Kobo data from database."""

from datetime import datetime
from pathlib import Path

from loguru import logger

from src.config import load_project_uids
from src.queries import get_assets_data, get_choices_data, get_survey_metadata


def extract_data():
    """Extract data and save to parquet files."""
    # Setup
    data_dir = Path("data/raw")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    uids = load_project_uids()
    logger.info(f"Extracting data for {len(uids)} projects")
    
    # Extract assets
    logger.info("[1/3] Extracting assets metadata...")
    df_assets = get_assets_data(asset_ids=uids)
    assets_path = data_dir / "assets.parquet"
    df_assets.to_parquet(assets_path, index=False)
    logger.success(f"Assets: {len(df_assets)} rows saved to {assets_path}")
    
    # Extract survey questions
    logger.info("[2/3] Extracting survey questions...")
    df_survey = get_survey_metadata(asset_ids=uids)
    survey_path = data_dir / "survey.parquet"
    df_survey.to_parquet(survey_path, index=False)
    logger.success(f"Survey: {len(df_survey)} rows saved to {survey_path}")
    
    # Extract choices
    logger.info("[3/3] Extracting choices (this may take a while)...")
    df_choices = get_choices_data(asset_ids=uids)
    choices_path = data_dir / "choices.parquet"
    df_choices.to_parquet(choices_path, index=False)
    logger.success(f"Choices: {len(df_choices)} rows saved to {choices_path}")
    
    # Summary
    logger.info("="*60)
    logger.success("Extraction completed successfully!")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Data saved in: {data_dir.absolute()}")
    logger.info(f"  - assets.parquet   : {len(df_assets):,} rows")
    logger.info(f"  - survey.parquet   : {len(df_survey):,} rows")
    logger.info(f"  - choices.parquet  : {len(df_choices):,} rows")
    logger.info("="*60)
