"""Query functions for Kobo assets (projects) metadata."""

from typing import Optional

import pandas as pd

from src.db import DatabaseConnection


def get_assets_data(
    asset_ids: Optional[list[str]] = None,
    name_pattern: Optional[str] = None,
) -> pd.DataFrame:
    """
    Retrieve assets (Kobo projects) information.
    
    Args:
        asset_ids: List of asset UIDs to filter by
        name_pattern: Regex pattern to filter asset names
        
    Returns:
        DataFrame with project information from asset table
    """
    db = DatabaseConnection()
    
    query = """
    SELECT 
        uid,
        name,
        owner__username,
        owner__organization,
        settings__organization,
        settings__sector__label as sector,
        date_created,
        date_modified,
        date_deployed,
        deployment__last_submission_time as last_submission,
        deployment__submission_count as submission_count,
        deployment__active as is_active,
        deployment_status,
        has_deployment,
        asset_type,
        settings__description as description
    FROM asset
    WHERE 1=1
    """
    
    params = {}
    
    if asset_ids and name_pattern:
        query += " AND (uid = ANY(:asset_ids) OR name ~ :name_pattern)"
        params["asset_ids"] = asset_ids
        params["name_pattern"] = name_pattern
    elif asset_ids:
        query += " AND uid = ANY(:asset_ids)"
        params["asset_ids"] = asset_ids
    elif name_pattern:
        query += " AND name ~ :name_pattern"
        params["name_pattern"] = name_pattern
    
    query += " ORDER BY date_modified DESC"
    
    return db.execute_query(query, params)
