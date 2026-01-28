"""Query functions for Kobo choices data."""

from typing import Optional

import pandas as pd

from src.db import DatabaseConnection


def get_choices_data(
    asset_ids: Optional[list[str]] = None,
    name_pattern: Optional[str] = None,
) -> pd.DataFrame:
    """
    Retrieve choices data for select_one and select_multiple questions.
    
    Args:
        asset_ids: List of asset UIDs to filter by
        name_pattern: Regex pattern to filter asset names
        
    Returns:
        DataFrame with columns: asset_uid, asset_name, question_name, question_type, 
                                list_name, choice_name, choice_label
    """
    db = DatabaseConnection()
    
    query = """
    SELECT 
        a.uid as asset_uid,
        a.name as asset_name,
        acs.name as question_name,
        acs.type as question_type,
        TRIM(REGEXP_REPLACE(acs.type, '^(select_one|select_multiple)\\s+', '')) as list_name,
        acc.name as choice_name,
        acc.label as choice_label,
        acc._autovalue as choice_autovalue,
        acs._kuid as question_kuid,
        acc._dlt_list_idx as choice_order
    FROM asset a
    INNER JOIN asset_content ac ON a.uid = ac._asset_uid
    INNER JOIN asset_content__survey acs ON ac._dlt_id = acs._dlt_parent_id
    INNER JOIN asset_content__choices acc ON 
        ac._dlt_id = acc._dlt_parent_id 
        AND TRIM(REGEXP_REPLACE(acs.type, '^(select_one|select_multiple)\\s+', '')) = acc.list_name
    WHERE (acs.type LIKE 'select_one %' OR acs.type LIKE 'select_multiple %')
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
    
    query += " ORDER BY a.name, acs._dlt_list_idx, acc._dlt_list_idx"
    
    return db.execute_query(query, params)
