"""Column presence analysis comparing country MSNAs to template."""

from pathlib import Path
import pandas as pd
from loguru import logger


def generate_column_presence_matrix(
    template_columns: list[str],
    assets_df: pd.DataFrame,
    survey_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate presence matrix showing which template columns exist in each MSNA.
    
    Args:
        template_columns: List of column names from template survey
        assets_df: Asset metadata (uid, name, country_code_settings, submission_count)
        survey_df: Survey data with asset_uid for joining
        
    Returns:
        DataFrame with index=project_name, columns=[country_code, submissions, col1, col2, ...]
        where template column values are 1 (present AND non-null) or 0 (absent OR null)
    """
    logger.info(f"Generating column presence matrix for {len(assets_df)} projects")
    
    # Map template column names to survey_df columns (some have different naming)
    column_mapping = {
        'level': None,       # Not in KoBo survey table
        'theme': None,       # Not in KoBo survey table
        'module': None,      # Not in KoBo survey table
        'indicator': None,   # Not in KoBo survey table
        'index': None,       # Not in KoBo survey table
        # Direct mappings - these are in asset_content__survey
        'type': 'type',
        'name': 'name',
        'label::english (en)': 'label::english (en)',
        'label::french (fr)': 'label::french (fr)',
        'hint::english (en)': 'hint::english (en)',
        'hint::french (fr)': 'hint::french (fr)',
        'calculation': 'calculation',
        'required': 'required',
        'relevant': 'relevant',
        'constraint': 'constraint',
        'default': 'default',
        'repeat_count': 'repeat_count',
        'constraint_message::english (en)': 'constraint_message::english (en)',
        'constraint_message::french (fr)': 'constraint_message::french (fr)',
        'appearance': 'appearance',
        'choice_filter': 'choice_filter',
        'parameters': 'parameters'
    }
    
    results = []
    
    for uid in assets_df['uid']:
        # Get project metadata
        project = assets_df[assets_df['uid'] == uid].iloc[0]
        
        # Get survey data for this project
        project_survey = survey_df[survey_df['asset_uid'] == uid]
        
        if project_survey.empty:
            logger.warning(f"No survey data for {project['name']}")
            continue
        
        # Check which template columns exist AND have non-null values
        presence = {}
        for template_col in template_columns:
            survey_col = column_mapping.get(template_col)
            
            if survey_col is None:
                # Column doesn't exist in survey table (like theme, module, etc.)
                presence[template_col] = 0
            elif survey_col in project_survey.columns:
                # Column exists - check if ANY question has non-null value
                has_values = project_survey[survey_col].notna().any()
                presence[template_col] = 1 if has_values else 0
            else:
                # Column should exist but doesn't (missing in this project)
                presence[template_col] = 0
        
        # Build row
        row = {
            'project_name': project['name'],
            'country_code': project['country_code_settings'],
            'submissions': project['submission_count'],
            **presence
        }
        results.append(row)
        
        n_present = sum(presence.values())
        logger.debug(f"{project['country_code_settings']} - {project['name']}: {n_present}/{len(template_columns)} columns")
    
    # Create DataFrame
    df = pd.DataFrame(results)
    df = df.set_index('project_name')
    df = df.sort_values('country_code')
    
    logger.info(f"Generated matrix: {len(df)} projects × {len(template_columns)} template columns")
    
    return df
