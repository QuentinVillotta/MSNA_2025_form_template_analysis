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
        -- Template columns from asset_content__survey
        acs.type,
        acs.name,
        acs.label_english_enx as "label::english (en)",
        acs.label_french_frx as "label::french (fr)",
        acs.hint_english_enx as "hint::english (en)",
        acs.hint_french_frx as "hint::french (fr)",
        acs.calculation,
        acs.required,
        acs.relevant,
        acs.constraint,
        acs.default,
        acs.repeat_count,
        acs.constraint_message_english_enx as "constraint_message::english (en)",
        acs.constraint_message_french_frx as "constraint_message::french (fr)",
        acs.appearance,
        acs.choice_filter,
        acs.parameters,
        -- Internal KoBo fields
        acs._kuid,
        acs._qpath,
        acs._dlt_list_idx as question_order,
        acs._dlt_parent_id
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
