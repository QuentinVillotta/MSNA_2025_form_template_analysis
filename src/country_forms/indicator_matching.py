"""Indicator name matching analysis between template and country MSNAs."""

from pathlib import Path
import pandas as pd
from loguru import logger


def generate_indicator_match_matrix(
    template_survey_df: pd.DataFrame,
    ib_df: pd.DataFrame,
    country_survey_df: pd.DataFrame,
    assets_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate detailed matrix showing which template indicators match in each country.
    
    Args:
        template_survey_df: Template survey with columns including 'name' for indicator names
        ib_df: Indicator Bank with tier/theme/module information
        country_survey_df: Survey data from all countries with 'name' column
        assets_df: Asset metadata with country information
        
    Returns:
        DataFrame with:
        - Index: Template indicator names
        - Columns: [theme, module, tier, country_code1, country_code2, ...]
        - Values: 1 if indicator exists in country, 0 otherwise
    """
    logger.info("Generating indicator match matrix (indicators × countries)")
    
    # Get template indicators (filter out groups/notes)
    template_indicators = template_survey_df[
        template_survey_df['type'].notna() & 
        ~template_survey_df['type'].str.startswith(('begin', 'end', 'note'))
    ]['name'].dropna().unique()
    
    logger.info(f"Found {len(template_indicators)} indicators in template")
    
    # Build matrix
    results = []
    
    for indicator_name in template_indicators:
        # Get metadata from template
        indicator_row = template_survey_df[template_survey_df['name'] == indicator_name].iloc[0]
        theme = indicator_row.get('theme', '')
        module = indicator_row.get('module', '')
        
        # Try to match with IB to get tier (IB has 'Question code' column)
        ib_match = ib_df[ib_df['Question code'] == indicator_name]
        tier = ib_match['Tier (1, 2 or 3)'].iloc[0] if not ib_match.empty else None
        
        row = {
            'indicator_name': indicator_name,
            'theme': theme,
            'module': module,
            'tier': tier
        }
        
        # Check presence in each country project (one column per survey, not per country)
        for _, asset in assets_df.iterrows():
            survey_name = asset['name']
            uid = asset['uid']
            
            # Get country survey data
            country_indicators = country_survey_df[
                country_survey_df['asset_uid'] == uid
            ]['name'].dropna().unique()
            
            # Check if indicator exists in this specific survey
            row[survey_name] = 1 if indicator_name in country_indicators else 0
        
        results.append(row)
    
    df = pd.DataFrame(results)
    df = df.set_index('indicator_name')
    
    logger.info(f"Generated matrix: {len(df)} indicators × {len(assets_df)} countries")
    
    return df


def generate_country_match_summary(
    template_survey_df: pd.DataFrame,
    ib_df: pd.DataFrame,
    country_survey_df: pd.DataFrame,
    assets_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate summary showing match statistics for each country MSNA.
    
    Args:
        template_survey_df: Template survey with indicator names
        ib_df: Indicator Bank with tier information
        country_survey_df: Survey data from all countries
        assets_df: Asset metadata with country information
        
    Returns:
        DataFrame with:
        - Index: Country survey names
        - Columns: [country_code, theme, module, tier, n_matched, n_not_matched, match_pct]
    """
    logger.info("Generating country match summary (countries × metrics)")
    
    # Get template indicators
    template_indicators = template_survey_df[
        template_survey_df['type'].notna() & 
        ~template_survey_df['type'].str.startswith(('begin', 'end', 'note'))
    ]['name'].dropna().unique()
    
    total_indicators = len(template_indicators)
    logger.info(f"Comparing against {total_indicators} template indicators")
    
    results = []
    
    for _, asset in assets_df.iterrows():
        uid = asset['uid']
        survey_name = asset['name']
        country_code = asset['country_code_settings']
        
        # Get country indicators
        country_indicators = country_survey_df[
            country_survey_df['asset_uid'] == uid
        ]['name'].dropna().unique()
        
        # Calculate matches
        matched = set(template_indicators) & set(country_indicators)
        n_matched = len(matched)
        n_not_matched = total_indicators - n_matched
        match_pct = round((n_matched / total_indicators) * 100, 1) if total_indicators > 0 else 0
        
        # Get theme/module/tier for matched indicators (aggregate)
        # For simplicity, we'll use the most common values or leave empty for now
        # These columns are meant for groupby operations
        
        row = {
            'survey_name': survey_name,
            'country_code': country_code,
            'theme': None,  # Will be used for groupby filtering
            'module': None,  # Will be used for groupby filtering
            'tier': None,  # Will be used for groupby filtering
            'n_total_indicators': total_indicators,
            'n_matched': n_matched,
            'n_not_matched': n_not_matched,
            'match_pct': match_pct
        }
        
        results.append(row)
        
        logger.debug(f"{country_code} - {survey_name}: {n_matched}/{total_indicators} matched ({match_pct}%)")
    
    df = pd.DataFrame(results)
    df = df.set_index('survey_name')
    df = df.sort_values('match_pct', ascending=False)
    
    logger.info(f"Generated summary: {len(df)} countries")
    
    return df
