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
        a.uid,
        a.name,
        a.owner__username,
        a.owner__organization,
        a.settings__organization,
        a.settings__sector__label as sector,
        a.date_created,
        a.date_modified,
        a.date_deployed,
        a.deployment__last_submission_time as last_submission,
        a.deployment__submission_count as submission_count,
        a.deployment__active as is_active,
        a.deployment_status,
        a.has_deployment,
        a.asset_type,
        a.settings__description as description,
        cc.label as country_name,
        cc.value as country_code_settings,
        SUBSTRING(a.name FROM '^([A-Z]{3})') as country_code_from_project_name
    FROM asset a
    LEFT JOIN asset__settings__country cc ON a._dlt_id = cc._dlt_parent_id
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
