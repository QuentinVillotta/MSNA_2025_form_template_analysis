"""Query functions for Kobo asset survey metadata (questions)."""

from typing import Optional

import pandas as pd

from src.db import DatabaseConnection


def get_survey_metadata(
    asset_ids: Optional[list[str]] = None,
    name_pattern: Optional[str] = None,
) -> pd.DataFrame:
    """
    Retrieve survey metadata (questions and types) from asset_content__survey.
    
    Args:
        asset_ids: List of asset UIDs to filter by
        name_pattern: Regex pattern to filter asset names
        
    Returns:
        DataFrame with columns: asset_uid, asset_name, question_name, question_type, etc.
    """
    db = DatabaseConnection()
    
    query = """
    SELECT 
        a.uid as asset_uid,
        a.name as asset_name,
        acs.name as question_name,
        acs.type as question_type,
        acs._kuid as question_kuid,
        acs._qpath as question_qpath,
        acs.required as question_required,
        acs._dlt_list_idx as question_order
    FROM asset a
    INNER JOIN asset_content ac ON a.uid = ac._asset_uid
    INNER JOIN asset_content__survey acs ON ac._dlt_id = acs._dlt_parent_id
    WHERE 1=1
    """
    
    params = {}
    
    if asset_ids and name_pattern:
        query += " AND (a.uid = ANY(:asset_ids) OR a.name ~ :name_pattern)"
        params["asset_ids"] = asset_ids
        params["name_pattern"] = name_pattern
    elif asset_ids:
        query += " AND a.uid = ANY(:asset_ids)"
        params["asset_ids"] = asset_ids
    elif name_pattern:
        query += " AND a.name ~ :name_pattern"
        params["name_pattern"] = name_pattern
    
    query += " ORDER BY a.name, acs._dlt_list_idx"
    
    return db.execute_query(query, params)
