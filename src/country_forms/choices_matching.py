"""Choices compliance analysis - matching template choices with country forms."""

from typing import Optional

import pandas as pd
from loguru import logger


def load_template_choices(template) -> pd.DataFrame:
    """
    Load choices from template Excel file.
    
    Args:
        template: TemplateLoader instance
        
    Returns:
        DataFrame with columns: list_name, name, label_en, label_fr (and other metadata)
    """
    choices_df = template.choices.copy()
    
    # Basic validation
    required_cols = ['list_name', 'name']
    missing_cols = [col for col in required_cols if col not in choices_df.columns]
    if missing_cols:
        raise ValueError(f"Template choices missing required columns: {missing_cols}")
    
    # Rename multilingual label columns for easier access
    label_cols = {col: col.replace('label::', '').replace(' ', '_').replace('(', '').replace(')', '') 
                  for col in choices_df.columns if col.startswith('label::')}
    if label_cols:
        choices_df = choices_df.rename(columns=label_cols)
    
    # Remove rows where both list_name and name are NaN (empty rows)
    choices_df = choices_df.dropna(subset=['list_name', 'name'], how='all')
    
    logger.info(f"Loaded {len(choices_df)} template choices across {choices_df['list_name'].nunique()} lists")
    
    return choices_df


def extract_country_choices(
    survey_df: pd.DataFrame, 
    assets_df: pd.DataFrame,
    choices_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Extract choices from country survey data.
    
    NOTE: This function now reads from choices.parquet instead of parsing survey_df.
    The survey_df parameter is kept for compatibility but not used.
    
    Args:
        survey_df: Country survey questions (from survey.parquet) - NOT USED
        assets_df: Assets metadata (for survey names and country codes)
        choices_df: Optional pre-loaded choices DataFrame. If None, loads with corrections applied.
        
    Returns:
        DataFrame with columns: asset_uid, survey_name, country_code, question_name, 
                                list_name, choice_name, choice_label
    """
    # If choices_df not provided, load with data corrections applied
    if choices_df is None:
        from src.data_loader import load_data
        _, _, choices_df = load_data()
        logger.info("Loaded choices data with corrections applied")
    
    if choices_df is None or len(choices_df) == 0:
        logger.error("No choices data available")
        return pd.DataFrame()
    
    # Merge with assets to get survey_name and country_code
    # choices.parquet has: asset_uid, asset_name, question_name, list_name, choice_name, choice_label
    # We need to add: survey_name, country_code from assets_df
    
    merged = choices_df.merge(
        assets_df[['uid', 'name', 'country_code_settings']],
        left_on='asset_uid',
        right_on='uid',
        how='left'
    )
    
    # Select and rename columns to match expected output
    country_choices_df = merged[[
        'asset_uid',
        'name',
        'country_code_settings',
        'question_name',
        'list_name',
        'choice_name',
        'choice_label'
    ]].rename(columns={
        'name': 'survey_name',
        'country_code_settings': 'country_code'
    })
    
    # Remove rows with missing critical data
    country_choices_df = country_choices_df.dropna(subset=['list_name', 'choice_name'])
    
    if len(country_choices_df) > 0:
        logger.info(f"Extracted {len(country_choices_df)} country choices across "
                   f"{country_choices_df['list_name'].nunique()} lists")
    else:
        logger.warning("No country choices extracted")
    
    return country_choices_df


def generate_choices_match_matrix(
    template_choices: pd.DataFrame,
    country_choices: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate binary matrix showing which template choices are present in each country.
    
    Args:
        template_choices: Template choices DataFrame (from load_template_choices)
        country_choices: Country choices DataFrame (from extract_country_choices)
        
    Returns:
        DataFrame with template choices as rows (list_name + choice_name) and 
        country surveys as columns (1=present, 0=absent)
    """
    if len(country_choices) == 0:
        logger.warning("No country choices to match")
        return pd.DataFrame()
    
    # Create unique identifiers for template choices
    template_choices['choice_id'] = (
        template_choices['list_name'].astype(str) + '::' + 
        template_choices['name'].astype(str)
    )
    
    # Create unique identifiers for country choices
    country_choices['choice_id'] = (
        country_choices['list_name'].astype(str) + '::' + 
        country_choices['choice_name'].astype(str)
    )
    
    # Get unique surveys
    surveys = country_choices['survey_name'].unique()
    
    # Initialize matrix with template choices as index
    match_matrix = pd.DataFrame(
        index=template_choices['choice_id'].unique(),
        columns=surveys
    )
    
    # Add metadata columns (use first label column found)
    label_cols = [col for col in template_choices.columns if col.startswith('label') or 'english' in col.lower()]
    metadata_cols = ['list_name', 'name']
    if label_cols:
        metadata_cols.append(label_cols[0])
    
    template_lookup = template_choices.set_index('choice_id')[metadata_cols].drop_duplicates()
    match_matrix = match_matrix.join(template_lookup, how='left')
    
    # Fill match matrix
    for survey in surveys:
        survey_choices = set(country_choices[country_choices['survey_name'] == survey]['choice_id'].unique())
        match_matrix[survey] = match_matrix.index.isin(survey_choices).astype(int)
    
    logger.success(f"Generated choices match matrix: {len(match_matrix)} template choices × {len(surveys)} surveys")
    
    return match_matrix


def generate_choices_summary(
    template_choices: pd.DataFrame,
    country_choices: pd.DataFrame,
    assets_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate summary statistics for choices compliance by country.
    
    Args:
        template_choices: Template choices DataFrame
        country_choices: Country choices DataFrame
        assets_df: Assets metadata
        
    Returns:
        DataFrame with columns: survey_name, country_code, n_template_choices, 
                                n_matched_choices, n_country_only_choices, match_pct
    """
    if len(country_choices) == 0:
        logger.warning("No country choices for summary")
        return pd.DataFrame()
    
    # Create unique identifiers
    template_choices['choice_id'] = (
        template_choices['list_name'].astype(str) + '::' + 
        template_choices['name'].astype(str)
    )
    country_choices['choice_id'] = (
        country_choices['list_name'].astype(str) + '::' + 
        country_choices['choice_name'].astype(str)
    )
    
    template_choice_ids = set(template_choices['choice_id'].unique())
    
    # Calculate per-survey statistics
    summary_records = []
    
    for survey_name in country_choices['survey_name'].unique():
        survey_data = country_choices[country_choices['survey_name'] == survey_name]
        country_code = survey_data.iloc[0]['country_code']
        
        country_choice_ids = set(survey_data['choice_id'].unique())
        
        n_template = len(template_choice_ids)
        n_matched = len(template_choice_ids & country_choice_ids)
        n_country_only = len(country_choice_ids - template_choice_ids)
        match_pct = (n_matched / n_template * 100) if n_template > 0 else 0
        
        summary_records.append({
            'survey_name': survey_name,
            'country_code': country_code,
            'n_template_choices': n_template,
            'n_matched_choices': n_matched,
            'n_country_only_choices': n_country_only,
            'match_pct': round(match_pct, 1)
        })
    
    summary_df = pd.DataFrame(summary_records).sort_values('match_pct', ascending=False)
    
    logger.success(f"Generated choices summary for {len(summary_df)} countries")
    
    return summary_df


def generate_list_name_matrix(
    template_choices: pd.DataFrame,
    country_choices: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate binary matrix showing which template list_names are present in each country.
    
    Args:
        template_choices: Template choices DataFrame
        country_choices: Country choices DataFrame
        
    Returns:
        DataFrame with template list_names as rows and surveys as columns (1=present, 0=absent)
    """
    if len(country_choices) == 0:
        logger.warning("No country choices for list_name matrix")
        return pd.DataFrame()
    
    template_lists = set(template_choices['list_name'].dropna().unique())
    surveys = country_choices['survey_name'].unique()
    
    # Initialize matrix
    match_matrix = pd.DataFrame(
        index=sorted(template_lists),
        columns=surveys
    )
    match_matrix.index.name = 'list_name'
    
    # Fill matrix
    for survey in surveys:
        survey_lists = set(country_choices[country_choices['survey_name'] == survey]['list_name'].dropna().unique())
        match_matrix[survey] = match_matrix.index.isin(survey_lists).astype(int)
    
    logger.success(f"Generated list_name matrix: {len(match_matrix)} lists × {len(surveys)} surveys")
    
    return match_matrix


def generate_list_name_summary(
    template_choices: pd.DataFrame,
    country_choices: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate summary statistics for list_name coverage by country.
    
    Args:
        template_choices: Template choices DataFrame
        country_choices: Country choices DataFrame
        
    Returns:
        DataFrame with columns: survey_name, country_code, n_template_lists, 
                                n_matched_lists, match_pct
    """
    if len(country_choices) == 0:
        logger.warning("No country choices for list_name summary")
        return pd.DataFrame()
    
    template_lists = set(template_choices['list_name'].dropna().unique())
    
    summary_records = []
    
    for survey_name in country_choices['survey_name'].unique():
        survey_data = country_choices[country_choices['survey_name'] == survey_name]
        country_code = survey_data.iloc[0]['country_code']
        
        country_lists = set(survey_data['list_name'].dropna().unique())
        
        n_template = len(template_lists)
        n_matched = len(template_lists & country_lists)
        match_pct = (n_matched / n_template * 100) if n_template > 0 else 0
        
        summary_records.append({
            'survey_name': survey_name,
            'country_code': country_code,
            'n_template_lists': n_template,
            'n_matched_lists': n_matched,
            'match_pct': round(match_pct, 1)
        })
    
    summary_df = pd.DataFrame(summary_records).sort_values('match_pct', ascending=False)
    
    logger.success(f"Generated list_name summary for {len(summary_df)} countries")
    
    return summary_df


def compare_choices_for_list(
    template_choices: pd.DataFrame,
    country_choices: pd.DataFrame,
    survey_name: str,
    list_name: str
) -> pd.DataFrame:
    """
    Compare choices between template and a specific country survey for a given list.
    
    Args:
        template_choices: Template choices DataFrame
        country_choices: Country choices DataFrame
        survey_name: Survey to compare
        list_name: Choice list to analyze
        
    Returns:
        DataFrame with columns: choice_name, in_template, in_country, status
    """
    # Get template choices for this list
    template_list = template_choices[template_choices['list_name'] == list_name]['name'].dropna().unique()
    
    # Get country choices for this list
    country_list = country_choices[
        (country_choices['survey_name'] == survey_name) & 
        (country_choices['list_name'] == list_name)
    ]['choice_name'].dropna().unique()
    
    # Build comparison
    all_choices = set(template_list) | set(country_list)
    
    # If no choices found, return empty DataFrame with correct structure
    if not all_choices:
        logger.warning(f"No choices found for list '{list_name}' in {survey_name}")
        return pd.DataFrame(columns=['choice_name', 'in_template', 'in_country', 'status'])
    
    comparison_records = []
    for choice in sorted(all_choices):
        in_template = choice in template_list
        in_country = choice in country_list
        
        if in_template and in_country:
            status = 'Match'
        elif in_template and not in_country:
            status = 'Missing in country'
        else:
            status = 'Country only'
        
        comparison_records.append({
            'choice_name': choice,
            'in_template': in_template,
            'in_country': in_country,
            'status': status
        })
    
    comparison_df = pd.DataFrame(comparison_records)
    
    logger.info(f"Compared list '{list_name}' for {survey_name}: "
               f"{len(comparison_df[comparison_df['status'] == 'Match'])} matches, "
               f"{len(comparison_df[comparison_df['status'] == 'Missing in country'])} missing, "
               f"{len(comparison_df[comparison_df['status'] == 'Country only'])} country-only")
    
    return comparison_df
